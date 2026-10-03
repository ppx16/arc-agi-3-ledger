"""A generic, non-learning model-based explorer for ARC-AGI-3.

WHY THIS SHAPE (the whole argument, so it can be checked rather than believed)
    The competition score is `mean over games of  sum(score_i * i) / sum(i)` where
    `score_i = min(100 * (human_actions_i / our_actions_i) ** 2, 115)` and an uncompleted
    level scores 0. Level 1 carries weight 1 of sum(1..L) -- for a 7-level game, 1/28 -- so
    *completing level 1 of every game at human efficiency scores 100/28 = 3.57*, against a
    published top-10% cut of 3.80. We do not need to solve these games. We need to finish
    LEVEL 1 of as many as possible within the 80 actions the harness allows.

    The shipped StochasticGoose scores ~0.18 on the hidden set, and **0.00 measured locally**.
    Reading its code explains why -- its training signal is
        reward = 1.0 if the frame changed else 0.0
    and it fits a CNN to that reward online, inside a single 80-action episode, resetting the
    network every time the level changes. That is a novelty detector trained on at most 80
    labelled samples. THIS AGENT COMPUTES THE SAME SIGNAL EXACTLY, WITHOUT LEARNING: keep a
    transition model keyed by the frame and prefer actions whose outcome is new.

⚠️ THE BUG THIS FILE EXISTS TO FIX (v1 measured 2/25 games even with a 2000-action budget)
    Hashing the RAW frame is broken whenever the frame contains a counter/timer/status bar,
    because those pixels change on *every* step. Every step then looks like a brand-new state,
    so `visits[successor]` is always 0, the "least-visited successor" tier carries no
    information at all, and the model never sees a repeated state. The exploration rule
    silently degrades into a random walk. That is an algorithmic failure, not a budget one --
    which is exactly what the 2000-action measurement showed.

    Fix: a **change-frequency mask**. Track, per cell, how often it differs from the previous
    frame, and zero out cells that change on >`MASK_FREQ` of steps before hashing. A HUD
    counter is masked; the board is not. Kept at 0.95 (not lower) because over-masking a
    click game can collapse the whole board to a single state.

    `ARC_SIG_MODE` selects the state identity so the three can be ablated without editing:
        raw      -- v1 behaviour, hash of the raw grid (the control)
        masked   -- hash of the change-frequency-masked grid          (default)
        objects  -- (bg, sorted (colour, centroid) of small components), no pixels at all

HARNESS FACTS USED HERE, each verified in the shipped code rather than assumed
      * `Agent.MAX_ACTIONS = 80` and `Swarm` builds ONE agent per game: 80 actions is the whole
        budget for the whole game, shared across all levels.
      * `frame` is `(1, 64, 64)` int8 colour indices 0..15; `win_levels` is in the frame.
      * `available_actions` arrives as RAW INTS (`[1,2,3,4]`, or `[6]` alone for click-only
        games), so a uniform pick over 1..7 would waste most of the budget.
      * ACTION6 coordinates go through `GameAction.set_data({"x","y"})` and DO reach the env,
        because the framework's `Agent.do_action_request` reads `action.action_data` and passes
        it as `data=`. (Calling `env.step(GameAction.ACTION6)` directly would drop them -- that
        caveat belongs to hand-rolled loop drivers, not to this agent.)
      * `Card.inc_reset_count` bumps `actions` for a non-full RESET, so RESET costs score -- but
        GAME_OVER is recoverable by RESET, which is strictly better than ending at 0.

Exploration rule (deterministic least-visited-successor / novelty walk):
    tier 0  the (state, action) pair has never been tried   -- highest priority
    tier 1  it leads to an already-seen state               -- fewer visits first
    tier 2  the frame did not change                        -- a no-op, uninformative
    tier 3  it is known to have caused GAME_OVER            -- last resort
Ties inside tier 0 break on a shuffle seeded by the state hash, so action ORDER varies between
states (better coverage than a fixed order) while a whole run stays exactly reproducible.
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

SIG_MODE = os.environ.get("ARC_SIG_MODE", "masked")
MASK_FREQ = 0.95          # a cell changing on >95% of steps is HUD, not board
MASK_MIN_OBS = 10         # don't mask before there is evidence
MAX_CLICK_CANDIDATES = 16
SMALL_OBJ = 64            # click targets are small sprites
_COARSE = 8


def _as_grid(frame: Any) -> Optional[np.ndarray]:
    """FrameData.frame -> a 2-D colour-index grid, or None if it is not usable."""
    if frame is None:
        return None
    try:
        a = np.asarray(frame)
    except Exception:
        return None
    if a.ndim == 3:
        if a.shape[0] < 1:
            return None
        a = a[0]
    if a.ndim != 2 or a.size == 0:
        return None
    return a.astype(np.int16, copy=False)


def _components(grid: np.ndarray, bg: int, min_area: int = 1, max_area: int = 1200
                ) -> list[tuple[int, int, int, int]]:
    """4-connected same-colour components -> [(area, colour, x, y) of centroid, ...]."""
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
                ys = sum(p[0] for p in cells) / len(cells)
                xs = sum(p[1] for p in cells) / len(cells)
                out.append((len(cells), colour, int(round(xs)), int(round(ys))))
    return out


class MyAgent(Agent):
    """Model-based novelty explorer. Deterministic; no learning, no torch, no training."""

    MAX_ACTIONS = 80

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._model: dict[str, dict[str, str]] = {}
        self._visits: dict[str, int] = {}
        self._noop: set[tuple[str, str]] = set()
        self._dead: set[tuple[str, str]] = set()
        self._pending: Optional[tuple[str, str]] = None
        self._level = -1
        self._clicks: list[tuple[int, int]] = []
        self._click_cache_sig: Optional[str] = None
        # change-frequency mask state (per level)
        self._prev_grid: Optional[np.ndarray] = None
        self._chg: Optional[np.ndarray] = None
        self._obs = 0
        self.resets = 0
        self.novelty_report: dict[str, Any] = {"sig_mode": SIG_MODE, "levels": 0,
                                               "level_actions": [], "states": 0,
                                               "resets": 0, "game_overs": 0, "masked_cells": 0}

    # ── state identity ────────────────────────────────────────────────────────────
    def _reset_mask(self) -> None:
        self._prev_grid = None
        self._chg = None
        self._obs = 0

    def _observe(self, grid: np.ndarray) -> None:
        """Accumulate per-cell change frequencies used by the mask."""
        if self._prev_grid is not None and self._prev_grid.shape == grid.shape:
            self._obs += 1
            if self._chg is None:
                self._chg = np.zeros(grid.shape, dtype=np.int32)
            self._chg += (self._prev_grid != grid)
        self._prev_grid = grid

    def _mask(self) -> Optional[np.ndarray]:
        if self._chg is None or self._obs < MASK_MIN_OBS:
            return None
        return (self._chg.astype(np.float32) / self._obs) > MASK_FREQ

    def _sig(self, grid: np.ndarray, levels: int) -> str:
        h = hashlib.blake2b(digest_size=8)
        h.update(bytes([levels & 0xFF]))
        if SIG_MODE == "objects":
            vals, counts = np.unique(grid, return_counts=True)
            bg = int(vals[int(np.argmax(counts))])
            comps = _components(grid, bg, min_area=1, max_area=SMALL_OBJ)
            h.update(repr(sorted((c, x, y) for (_a, c, x, y) in comps)).encode())
        else:
            g = grid
            if SIG_MODE == "masked":
                m = self._mask()
                if m is not None:
                    g = np.where(m, np.int16(-1), grid)
            h.update(g.tobytes())
        return h.hexdigest()

    # ── action vocabulary ─────────────────────────────────────────────────────────
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

    def _click_points(self, grid: np.ndarray, sig: str) -> list[tuple[int, int]]:
        """Candidate click coordinates. Click targets are SMALL sprites; non-target clicks are
        no-ops that dedup away, so a loose set is safe. Rarest colour first."""
        if self._click_cache_sig == sig:
            return self._clicks
        vals, counts = np.unique(grid, return_counts=True)
        bg = int(vals[int(np.argmax(counts))])
        freq = {int(v): int(c) for v, c in zip(vals, counts)}
        comps = _components(grid, bg, min_area=1, max_area=SMALL_OBJ)
        comps.sort(key=lambda t: (freq.get(t[1], 0), -t[0]))      # rare colour, then bigger
        pts = [(x, y) for (_a, _c, x, y) in comps[:MAX_CLICK_CANDIDATES]]
        if not pts:
            h, w = grid.shape
            step = max(1, min(h, w) // _COARSE)
            pts = [(c, r) for r in range(step // 2, h, step)
                   for c in range(step // 2, w, step)][:MAX_CLICK_CANDIDATES]
        self._clicks = pts
        self._click_cache_sig = sig
        return pts

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

    # ── the loop ──────────────────────────────────────────────────────────────────
    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        # GAME_OVER is NOT done: RESET restarts the current level, which beats ending at 0.
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        try:
            return self._choose(latest_frame)
        except Exception as e:                                    # never let the run die
            self.novelty_report["error"] = "%s: %s" % (type(e).__name__, e)
            return self._legal(latest_frame)[0]

    def _choose(self, latest_frame: FrameData) -> GameAction:
        state = latest_frame.state
        if state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            if state is GameState.GAME_OVER:
                self.novelty_report["game_overs"] += 1
            if self._pending is not None:
                self._dead.add(self._pending)          # this pair is what killed us
                self._pending = None
            self.resets += 1
            self.novelty_report["resets"] = self.resets
            return GameAction.RESET

        grid = _as_grid(latest_frame.frame)
        if grid is None:
            return self._legal(latest_frame)[0]

        levels = int(latest_frame.levels_completed or 0)
        if levels != self._level:
            if self._level >= 0:
                self.novelty_report["level_actions"].append(self.action_counter)
            self._level = levels
            self._model.clear()
            self._visits.clear()
            self._noop.clear()
            self._dead.clear()
            self._click_cache_sig = None
            self._pending = None
            self._reset_mask()                     # a new level has a new HUD and layout
            self.novelty_report["levels"] = levels

        self._observe(grid)
        sig = self._sig(grid, levels)
        m = self._mask()
        self.novelty_report["masked_cells"] = int(m.sum()) if m is not None else 0

        if self._pending is not None:
            psig, pkey = self._pending
            if psig != sig:
                self._model.setdefault(psig, {})[pkey] = sig
            else:
                self._noop.add((psig, pkey))
            self._pending = None
        self._visits[sig] = self._visits.get(sig, 0) + 1
        self.novelty_report["states"] = len(self._visits)

        cands = self._candidates(self._legal(latest_frame), grid, sig)
        known = self._model.get(sig, {})

        best: Optional[tuple[tuple[int, int, int], GameAction, str]] = None
        for i, (act, key) in enumerate(cands):
            pair = (sig, key)
            if pair in self._dead:
                rank = (3, 0, i)
            elif key not in known:
                rank = (0, 0, i)                       # unexplored: always first
            elif pair in self._noop or known[key] == sig:
                rank = (2, 0, i)                       # no-op: uninformative
            else:
                rank = (1, self._visits.get(known[key], 0), i)   # least-visited successor
            if best is None or rank < best[0]:
                best = (rank, act, key)

        assert best is not None
        _rank, act, key = best
        if act is GameAction.ACTION6:
            x, y = key[2:].split(",")
            act.set_data({"x": int(x), "y": int(y)})
        act.reasoning = "model-based novelty [%s] (%s)" % (SIG_MODE, key)
        self._pending = (sig, key)
        return act
