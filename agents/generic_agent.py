"""Generic ARC-AGI-3 agent: exact novelty model, WIDE click space, NO self-imposed action cap.

WHY THIS EXISTS, AND WHY IT IS NOT A LOCALLY-TUNED POLICY

    F37 is the reason. `56705048` (a portfolio of candidate orderings, chosen by sweeping ~30
    configurations) returned **0.08** on the hidden set, against its **0.2693** local score. That
    agent is DETERMINISTIC, so the same game set cannot give two scores -- **the rerun's games are
    not the 25 public games**, and local CV is not a leaderboard proxy. Worse, the ordering was
    anti-predictive: the best local score produced the worst hidden score.

    So this agent is justified by MECHANISM ONLY. No parameter here was chosen by a local score.

WHAT IS FIXED, AND WHY EACH FIX IS UNCONDITIONAL

    1. ⭐ NO ACTION CAP. `agent.py:22` sets `MAX_ACTIONS = 80`, but it is consulted only inside the
       agent's own `main()` loop (lines 74 and 179) -- the harness never enforces it.
       `goose_agent.py:122` overrides it with `float('inf')`, so the goose keeps playing while every
       agent this project wrote stopped dead at 80. That is strictly a limitation: stopping cannot
       score, and continuing can only add.

    2. ⭐⭐ THE SCORING IS PER LEVEL, NOT CUMULATIVE -- measured, not assumed. Through the shipped
       scorer on r11l:

           total_actions = 81     level_actions = [27, 54, 0, 0, 0, 0]
           level_scores  = [66.4, 0, ...]      baselines = [22, 33, 51, 26, 52, 49]

       and 100*(22/27)**2 = 66.4. **27 + 54 = 81**, so `level_actions[i]` is the spend INSIDE level
       i, not a running total. Two consequences that decide the whole strategy:
         * actions burned AFTER a level completes do NOT reduce that level's score -- only the spend
           up to its completion does;
         * every level therefore has its OWN budget, so reaching a later level is worth doing even
           if arriving there was expensive (later levels also carry MORE weight: level i counts i).
       ⇒ An agent that stops at 80 total actions can essentially only ever score level 1.

    3. ⚠️ WIDE CLICK SPACE. The goose's `ActionModel` has a coordinate head over all 64*64 = 4096
       cells (F36.2); every agent here clicked 12-16 object centroids. F34.3 measured that on `ft09`
       and `sc25` EVERY object-centroid click is a no-op -- those games are unreachable by
       construction. This agent unions the object centroids with a coarse lattice, so no game is
       structurally blind.

    4. ⚠️ NEVER FALL BACK TO A CONSTANT ACTION. `work/probe_avatar.py` crashed on `sp80` with
       `shapes (64,64) vs (0,)`: `env.step` demonstrably returns a degenerate frame. The old code
       answered that with `from_id(legal[0])` **every remaining step**, i.e. a guaranteed ~0 on any
       game that trips it. Here a degenerate frame keeps the last good grid, and if there is none the
       agent ROTATES through the legal actions instead of freezing on one.

    What is deliberately NOT here: any parameter tuned against the public 25.

Usage (local):  .venv\\Scripts\\python.exe score_local.py --agent ..\\agents\\generic_agent.py
⚠️ For a SUBMISSION the knobs must be baked in -- see work/mk_submission_agent.py; the rerun has no
   environment variables.
"""
from __future__ import annotations

import hashlib
import os
import random
from collections import deque
from typing import Any, Optional

import numpy as np

from agents.agent import Agent
from arcengine import FrameData, GameAction, GameState

# ⭐ (1) no SHORT self-imposed cap. Why 1200 and not `inf`:
#   * the old cap of 80 is smaller than ONE game's level budgets -- the 25 public games have 6-10
#     levels whose human baselines are 7-78 actions EACH, so a full solve is ~300-800 actions. 80
#     total actions cannot in principle reach even level 3.
#   * `inf` is what the goose uses, but our per-action cost is ~6 ms (measured: 25 games x 80 actions
#     in 12 s), so 1e6 actions would be ~100 minutes PER GAME and would risk a rerun timeout. The
#     goose pays the same risk with a much slower CNN.
#   ⇒ 1200 is chosen to cover a complete game with margin while keeping a worst case of ~7 s/game.
MAX_ACTIONS = int(float(os.environ.get("ARC_MAX_ACTIONS", "1200")))
MAX_CLICK_CANDIDATES = int(os.environ.get("ARC_MAX_CLICKS", "48"))
SMALL_OBJ = 400
LATTICE_STEP = int(os.environ.get("ARC_LATTICE", "8"))


def _as_grid(frame: Any) -> Optional[np.ndarray]:
    """FrameData.frame -> a 2-D int grid, or None if it is degenerate.

    ⚠️ Returns None rather than raising: `env.step` returns reshaped/empty frames on some games
    (measured on sp80), and an exception here used to be swallowed into a constant-action fallback.
    """
    if frame is None:
        return None
    try:
        a = np.asarray(frame)
    except Exception:
        return None
    if a.ndim == 3:
        if a.shape[0] < 1:
            return None
        a = a[0] if a.shape[0] == 1 else a[-1]      # 2-layer games: the last layer is the board
    if a.ndim != 2 or a.size == 0:
        return None
    return a.astype(np.int16, copy=False)


def _components(grid: np.ndarray, bg: int, min_area: int = 1, max_area: int = SMALL_OBJ
                ) -> list[tuple[int, int, int, int]]:
    """4-connected same-colour components -> [(area, colour, x, y), ...]."""
    h, w = grid.shape
    seen = np.zeros((h, w), dtype=bool)
    out: list[tuple[int, int, int, int]] = []
    for r in range(h):
        for c in range(w):
            if seen[r, c] or grid[r, c] == bg:
                continue
            colour = int(grid[r, c])
            q = deque([(r, c)])
            seen[r, c] = True
            cells = []
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and grid[ny, nx] == colour:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if min_area <= len(cells) <= max_area:
                ys = [p[0] for p in cells]
                xs = [p[1] for p in cells]
                out.append((len(cells), colour,
                            int(round(sum(xs) / len(xs))), int(round(sum(ys) / len(ys)))))
    return out


class MyAgent(Agent):
    """Exact-transition novelty walk (the goose's signal, computed instead of learned)."""

    MAX_ACTIONS = MAX_ACTIONS

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._model: dict[str, dict[str, str]] = {}
        self._visits: dict[str, int] = {}
        self._noop: set[tuple[str, str]] = set()
        self._dead: set[tuple[str, str]] = set()
        self._pending: Optional[tuple[str, str]] = None
        self._level = -1
        self._clicks: list[tuple[int, int]] = []
        self._click_sig: Optional[str] = None
        self._last_grid: Optional[np.ndarray] = None
        self._rotate = 0
        self._degenerate = 0
        self._resets = 0

    # ── action vocabulary ────────────────────────────────────────────────────────
    @staticmethod
    def _legal(latest_frame: FrameData) -> list[GameAction]:
        raw = getattr(latest_frame, "available_actions", None) or []
        acts: list[GameAction] = []
        for v in raw:
            try:
                a = v if isinstance(v, GameAction) else GameAction.from_id(int(v))
                if a not in acts:
                    acts.append(a)
            except Exception:
                continue
        return acts or [GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3,
                        GameAction.ACTION4, GameAction.ACTION5]

    def _fallback(self, latest_frame: FrameData, grid: Optional[np.ndarray]) -> GameAction:
        """⚠️ (4) ROTATE rather than freeze. A constant action guarantees a zero."""
        acts = self._legal(latest_frame)
        if grid is not None and GameAction.ACTION6 in acts and self._clicks:
            self._rotate += 1
            x, y = self._clicks[self._rotate % len(self._clicks)]
            a = GameAction.ACTION6
            a.set_data({"x": int(x), "y": int(y)})
            a.reasoning = "fallback rotating click"
            return a
        self._rotate += 1
        a = acts[self._rotate % len(acts)]
        a.reasoning = "fallback rotating action"
        return a

    def _click_points(self, grid: np.ndarray, sig: str) -> list[tuple[int, int]]:
        """Object centroids UNION a coarse lattice.

        ⚠️ (3) The centroids alone are a structural blind spot: F34.3 measured that every
        object-centroid click is a no-op on ft09 and sc25.
        """
        if self._click_sig == sig:
            return self._clicks
        vals, counts = np.unique(grid, return_counts=True)
        bg = int(vals[int(np.argmax(counts))])
        freq = {int(v): int(c) for v, c in zip(vals, counts)}
        comps = _components(grid, bg)
        comps.sort(key=lambda t: (freq.get(t[1], 0), -t[0]))
        pts: list[tuple[int, int]] = []
        for (_a, _c, x, y) in comps:
            if (x, y) not in pts:
                pts.append((x, y))
        step = max(2, LATTICE_STEP)
        for yy in range(step // 2, grid.shape[0], step):
            for xx in range(step // 2, grid.shape[1], step):
                if (xx, yy) not in pts:
                    pts.append((xx, yy))
        self._clicks = pts[:MAX_CLICK_CANDIDATES]
        self._click_sig = sig
        return self._clicks

    def _candidates(self, acts: list[GameAction], grid: np.ndarray, sig: str
                    ) -> list[tuple[GameAction, str]]:
        out: list[tuple[GameAction, str]] = []
        for a in acts:
            if a is GameAction.ACTION6:
                for (x, y) in self._click_points(grid, sig):
                    out.append((a, "6:%d,%d" % (x, y)))
            else:
                out.append((a, "%d" % int(a.value)))
        rng = random.Random(int(sig, 16))
        rng.shuffle(out)
        return out

    # ── loop ─────────────────────────────────────────────────────────────────────
    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        # GAME_OVER is NOT done: RESET restarts the CURRENT level, so completed levels survive it.
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        try:
            return self._choose(latest_frame)
        except Exception as e:                     # never let the run die
            print("[generic] choose_action error: %s: %s" % (type(e).__name__, e), flush=True)
            return self._fallback(latest_frame, self._last_grid)

    def _choose(self, latest_frame: FrameData) -> GameAction:
        state = latest_frame.state
        if state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            if self._pending is not None:
                self._dead.add(self._pending)
                self._pending = None
            self._resets += 1
            self._level = -1
            return GameAction.RESET

        grid = _as_grid(latest_frame.frame)
        if grid is None:
            # ⚠️ (4) degenerate frame: keep the last good grid, and never freeze on one action.
            self._degenerate += 1
            if self._last_grid is None:
                return self._fallback(latest_frame, None)
            grid = self._last_grid
        else:
            self._last_grid = grid

        levels = int(latest_frame.levels_completed or 0)
        if levels != self._level:
            self._level = levels
            self._model.clear()
            self._visits.clear()
            self._noop.clear()
            self._dead.clear()
            self._click_sig = None
            self._pending = None

        sig = hashlib.blake2b(bytes([levels & 0xFF]) + grid.tobytes(),
                              digest_size=8).hexdigest()
        if self._pending is not None:
            psig, pkey = self._pending
            if psig != sig:
                self._model.setdefault(psig, {})[pkey] = sig
            else:
                self._noop.add((psig, pkey))
            self._pending = None
        self._visits[sig] = self._visits.get(sig, 0) + 1

        cands = self._candidates(self._legal(latest_frame), grid, sig)
        known = self._model.get(sig, {})

        best: Optional[tuple[tuple[int, int, int], GameAction, str]] = None
        for i, (act, key) in enumerate(cands):
            pair = (sig, key)
            if pair in self._dead:
                rank = (3, 0, i)
            elif key not in known:
                rank = (0, 0, i)
            elif pair in self._noop or known[key] == sig:
                rank = (2, 0, i)
            else:
                rank = (1, self._visits.get(known[key], 0), i)
            if best is None or rank < best[0]:
                best = (rank, act, key)

        if best is None:
            return self._fallback(latest_frame, grid)
        _rank, act, key = best
        if act is GameAction.ACTION6:
            x, y = key[2:].split(",")
            act.set_data({"x": int(x), "y": int(y)})
        act.reasoning = "exact novelty (%s)" % key
        self._pending = (sig, key)
        return act
