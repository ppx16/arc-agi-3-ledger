"""ARC-AGI-3 agent: plan the level from the frame, then execute the plan.

WHY PLANNING AND NOT SEARCHING  (FINDINGS F5)
    RHAE is `(human_actions / ai_actions) ** 2` per level, capped at 1.15. BFS to solve LS20's first
    level cost 1,777 env steps against a budget of ~41 actions, so a search-at-runtime agent scores
    ~0 even when guaranteed to win. Every env step a search takes is an action the metric charges for.

    So this agent derives the game's rules from the observed frame and computes the shortest action
    sequence **in process**, spending actions only on execution. On LS20 level 1 that finds
    `3331111444111` -- 13 actions, which BFS proves is optimal -- at **zero** action cost.

THE MODEL IT USES  (measured, not assumed -- F13/F14/F17/F18/F19)
    lattice      5-pixel steps anchored at the movable block
    passability  a cell is enterable iff its 5x5 footprint has >= 20 pixels of WALL colour,
                 or it is the block's own cell (vacating paints wall, so it can step back)
    goal         the unique lattice cell lying inside a colour-5 region enclosed by WALL colour
    collectible  lattice cells containing a pixel of the object colour (colour 1 in LS20);
                 entering one is FREE and advances the progress panel
    budget       the `$` bar = 2 cells per action, ~41 actions per level
    state        (cell, set of collectibles taken) -- NOT the cell alone (F15)

⚠️ HOW FAR THIS IS VERIFIED, STATED PLAINLY
    Verified **end to end on LS20 level 1**. The rules are consistent on level 2 but the level-2 plan
    FAILS (F20/F21) and the cause is unknown. On any other game none of these rules is known to hold.
    So the planner is tried first and **everything else falls back** to a legal-action novelty walk.
    The fallback is deliberately simple -- on an unmodelled game scoring is a lottery -- but never
    wasting an action on an illegal command is still strictly better than the shipped starter, which
    picks uniformly from ALL actions while six of the 25 games accept only one of them.

⚠️ `RESET` RESTARTS THE CURRENT LEVEL, not the game (F2). Re-planning whenever the level changes is
    therefore cheap and safe: the plan is always computed from the frame actually in front of us.
"""
from __future__ import annotations

import random
from collections import deque
from typing import Any

import numpy as np

from arcengine import FrameData, GameAction, GameState

from agents.agent import Agent

WALL = 3
OBJ_COLOURS = (1,)
WALL_MIN = 20
MOVES = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}   # action -> (drow, dcol) in lattice cells
STEP = 5


# ── the model ────────────────────────────────────────────────────────────────────────────────
def _grid(frame: FrameData):
    a = np.asarray(frame.frame)
    return (a[-1] if a.ndim == 3 else a).astype(np.uint8)


def _find_block(g):
    """The movable block as an exact 5x5 stamp: two rows of 12 directly above three rows of 9.

    ⚠️ Matching on colour alone is wrong: colour 9 also draws the `@` patterns inside the panels, so
    a colour-based bounding box measures the whole board and never moves (F4b).
    """
    H, W = g.shape
    for r in range(H - 4):
        for c in range(W - 4):
            if np.all(g[r:r + 2, c:c + 5] == 12) and np.all(g[r + 2:r + 5, c:c + 5] == 9):
                return r, c
    return None


def _passable(g, r, c, start):
    if (r, c) == start:
        return True
    if not (0 <= r <= g.shape[0] - STEP and 0 <= c <= g.shape[1] - STEP):
        return False
    return int((g[r:r + 5, c:c + 5] == WALL).sum()) >= WALL_MIN


def _cells(start, H, W):
    rs = [start[0] + STEP * k for k in range(-12, 13) if 0 <= start[0] + STEP * k <= H - STEP]
    cs = [start[1] + STEP * k for k in range(-12, 13) if 0 <= start[1] + STEP * k <= W - STEP]
    return rs, cs


def _find_goal(g, start):
    """Lattice cells inside a colour-5 blob whose whole rim is WALL colour.

    Measured unique on LS20 level 1. The rigour matters: a panel whose rim is background -- a legend
    rather than a goal marker -- is excluded, which is what stops the bottom-left display being
    mistaken for the objective.
    """
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    boxes = []
    for r0 in range(H):
        for c0 in range(W):
            if g[r0, c0] != 5 or seen[r0, c0]:
                continue
            q, comp = deque([(r0, c0)]), []
            seen[r0, c0] = True
            while q:
                y, x = q.popleft()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny, nx] and g[ny, nx] == 5:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            ys = [p[0] for p in comp]
            xs = [p[1] for p in comp]
            a, b, c, d = min(ys), max(ys), min(xs), max(xs)
            ring = []
            if a - 1 >= 0:
                ring += [g[a - 1, x] for x in range(c, d + 1)]
            if b + 1 < H:
                ring += [g[b + 1, x] for x in range(c, d + 1)]
            if c - 1 >= 0:
                ring += [g[y, c - 1] for y in range(a, b + 1)]
            if d + 1 < W:
                ring += [g[y, d + 1] for y in range(a, b + 1)]
            if ring and len(comp) >= 9 and all(v == WALL for v in ring):
                boxes.append((a, b, c, d))
    rs, cs = _cells(start, H, W)
    out = []
    for r in rs:
        for c in cs:
            if (r, c) == start:
                continue
            for (a, b, cc, d) in boxes:
                if r >= a and r + 4 <= b and c >= cc and c + 4 <= d:
                    out.append((r, c))
                    break
    return out


def _find_collectibles(g, start):
    """Lattice cells containing a pixel of the object colour.

    ⚠️ Two earlier versions inferred "object" from the footprint's colour MIX and were wrong in both
    directions (F20a). Identifying the object by ITS OWN COLOUR is what is verified on both levels.
    """
    mask = np.isin(g, list(OBJ_COLOURS))
    if not mask.any():
        return []
    rs, cs = _cells(start, g.shape[0], g.shape[1])
    return [(r, c) for r in rs for c in cs
            if (r, c) != start and mask[r:r + 5, c:c + 5].any()]


def _plan(g, start):
    """BFS over (cell, collected). Returns a list of action ids, or None.

    The state must include the collectibles taken, not just the cell: two routes reach LS20's
    (15,34) and behave differently there, because one of them took the pickup (F15).
    """
    goals = set(_find_goal(g, start))
    picks = set(_find_collectibles(g, start))
    if not goals:
        return None
    q = deque([(start, frozenset(), [])])
    seen = {(start, frozenset())}
    while q:
        (r, c), got, path = q.popleft()
        if (r, c) in goals and path and picks <= got:
            return path
        for aid, (dr, dc) in MOVES.items():
            nr, nc = r + dr * STEP, c + dc * STEP
            if not (0 <= nr <= g.shape[0] - STEP and 0 <= nc <= g.shape[1] - STEP):
                continue
            # the goal is enterable by definition: the wall rule rejects its panel interior
            if not (_passable(g, nr, nc, start) or (nr, nc) in goals):
                continue
            ngot = got | ({(nr, nc)} if (nr, nc) in picks else set())
            st = ((nr, nc), ngot)
            if st in seen:
                continue
            seen.add(st)
            q.append(((nr, nc), ngot, path + [aid]))
    return None


# ── the agent ────────────────────────────────────────────────────────────────────────────────
class MyAgent(Agent):
    """Plan the level from the frame; fall back to a legal-action novelty walk."""

    MAX_ACTIONS = 80

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        random.seed(int(self.game_id.__hash__() & 0xFFFF) ^ 0xBEEF)
        self._plan: list[int] = []
        self._at = 0
        self._level = -1
        self._tried: dict[bytes, set] = {}
        self.report = {'planned': 0, 'failed': 0, 'fallback_actions': 0}

    @property
    def name(self) -> str:
        return f"{super().name}.planner"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def _replan(self, frame: FrameData) -> None:
        """Build a plan for the level we are actually on. Cheap and safe: RESET is per-level (F2)."""
        self._plan, self._at = [], 0
        try:
            g = _grid(frame)
            start = _find_block(g)
            if start is None:
                return
            acts = _plan(g, start)
            if acts:
                self._plan = acts
                self.report['planned'] += 1
            else:
                self.report['failed'] += 1
        except Exception:
            self.report['failed'] += 1

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return GameAction.RESET

        lvl = int(latest_frame.levels_completed or 0)
        if lvl != self._level:
            self._level = lvl
            self._replan(latest_frame)

        # ── execute the plan ─────────────────────────────────────────────────────────────────
        if self._at < len(self._plan):
            aid = self._plan[self._at]
            self._at += 1
            a = GameAction.from_id(aid)
            a.reasoning = {"why": "planned", "step": self._at, "of": len(self._plan), "level": lvl}
            return a

        # ── fallback: never spend an action on a command the game ignores ─────────────────────
        self.report['fallback_actions'] += 1
        legal = []
        for v in (latest_frame.available_actions or []):
            try:
                a = GameAction.from_id(int(v))
            except Exception:
                continue
            if a is not GameAction.RESET and a not in legal:
                legal.append(a)
        if not legal:
            return GameAction.RESET

        key = _grid(latest_frame).tobytes()
        tried = self._tried.setdefault(key, set())
        for a in legal:
            if a is GameAction.ACTION6:
                continue
            if a.name not in tried:
                tried.add(a.name)
                a.reasoning = {"why": "fallback: untried legal action"}
                return a
        a = random.choice(legal)
        if a is GameAction.ACTION6:
            a.set_data({"x": random.randint(0, 63), "y": random.randint(0, 63)})
        a.reasoning = {"why": "fallback: legal random"}
        return a
