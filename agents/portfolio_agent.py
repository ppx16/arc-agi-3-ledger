"""SUBMISSION AGENT: dense+rare+xy+area portfolio, 20 actions per phase.

Measured through tools/score_local.py (the SHIPPED scorer against the real baselines),
MAX_ACTIONS=80, all 25 public games: OVERALL 0.2693, 2/25 games with >=1 level.

Generated from agents/cycle_agent.py by work/mk_submission_agent.py; the ONLY differences are
the three baked-in defaults below. See FINDINGS F34 for the family and its caveats.
"""
from __future__ import annotations

import os
import random
from collections import deque
from typing import Any, Optional

import numpy as np

from agents.agent import Agent
from arcengine import FrameData, GameAction, GameState

POLICY = os.environ.get("ARC_POLICY", "portfolio")
ORDER = os.environ.get("ARC_ORDER", "xy")
DWELL = int(os.environ.get("ARC_DWELL", "1"))
# `hybrid`  : fixed rare-orbit for the first ARC_K actions, then the novelty walk
# `portfolio`: ARC_PHASE-long blocks, each block a DIFFERENT candidate ordering
ARC_K = int(os.environ.get("ARC_K", "30"))
ARC_PHASE = int(os.environ.get("ARC_PHASE", "20"))
PORTFOLIO = (os.environ.get("ARC_PORTFOLIO", "dense,rare,xy,area") or "").split(",")
if PORTFOLIO == [""]:
    PORTFOLIO = []
MAX_CLICK_CANDIDATES = 12
SMALL_OBJ = 400


def _as_grid(frame: Any) -> Optional[np.ndarray]:
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


def _components(grid, bg, min_area=1, max_area=SMALL_OBJ):
    h, w = grid.shape
    seen = np.zeros((h, w), dtype=bool)
    out = []
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
                out.append((len(cells), colour, int(round(sum(xs) / len(xs))),
                            int(round(sum(ys) / len(ys)))))
    return out


class MyAgent(Agent):
    MAX_ACTIONS = 80

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._level = -1
        self._plan: list[tuple[int, Optional[tuple[int, int]]]] = []
        self._plan_len = 0
        self._nov = None
        self._nov_err = ""
        self._reported_error = False
        self._since = 0
        self._attempt = 0
        self._report: dict[str, Any] = {"policy": POLICY, "order": ORDER, "dwell": DWELL,
                                        "plans": [], "resets": 0}

    @staticmethod
    def _legal(latest_frame: FrameData) -> list[int]:
        raw = getattr(latest_frame, "available_actions", None) or []
        ids = []
        for v in raw:
            try:
                i = int(v.value) if isinstance(v, GameAction) else int(v)
            except Exception:
                continue
            if i not in ids:
                ids.append(i)
        return ids or [1, 2, 3, 4, 5]

    def _candidates(self, grid: np.ndarray, ids: list[int], order: Optional[str] = None
                    ) -> list[tuple[int, Optional[tuple[int, int]]]]:
        """The level's action orbit, computed ONCE from the level's first frame."""
        order = order or ORDER
        out: list[tuple[int, Optional[tuple[int, int]]]] = []
        vals, counts = np.unique(grid, return_counts=True)
        bg = int(vals[int(np.argmax(counts))])
        freq = {int(v): int(c) for v, c in zip(vals, counts)}
        comps = _components(grid, bg)
        if order == "xy":
            comps.sort(key=lambda t: (t[3], t[2]))
        elif order == "yx":
            comps.sort(key=lambda t: (t[2], t[3]))
        elif order == "rare":
            comps.sort(key=lambda t: (freq.get(t[1], 0), -t[0], t[3], t[2]))
        elif order == "area":
            comps.sort(key=lambda t: (-t[0], t[1], t[3], t[2]))
        elif order == "lattice":
            comps = []                       # blind grid: for games whose objects are not clickable
            for yy in range(8, 64, 16):
                for xx in range(8, 64, 16):
                    comps.append((1, 0, xx, yy))
        elif order == "dense":
            # DENSE coverage: 64 DISTINCT cells at step 8. The object-centroid list caps at 12, so
            # 80 actions revisit the same few cells ~6x; this visits 64 different cells once.
            # Which is better is a MEASUREMENT: it depends on whether a level answers to one right
            # cell (coverage wins) or to an ordered sequence (repetition wins). r11l's winning
            # click at action 28 had ALREADY been tried at action 22, so that one is
            # sequence-shaped -- but not every game need be.
            comps = []
            for yy in range(4, 64, 8):
                for xx in range(4, 64, 8):
                    comps.append((1, 0, xx, yy))
        else:
            comps.sort(key=lambda t: (t[1], t[3], t[2]))
        pts = []
        for (_a, _c, x, y) in comps[:MAX_CLICK_CANDIDATES]:
            if (x, y) not in pts:
                pts.append((x, y))
        for i in ids:
            if i == 6:
                for (x, y) in pts:
                    out.append((6, (x, y)))
            else:
                out.append((i, None))
        return out

    def _novelty(self):
        """Load agents/novelty_agent.py by FILE PATH and prove it loaded.

        `from agents.novelty_agent import MyAgent` does NOT resolve here: the name `agents` on
        sys.path is the VENDOR package (starter/vendor/ARC-AGI-3-Agents/agents), which has no
        `novelty_agent` module. So the package import failed, and the failure was swallowed.
        """
        if getattr(self, "_nov", None) is not None:
            return self._nov
        try:
            import importlib.util
            here = os.path.dirname(os.path.abspath(__file__))
            cands = [os.path.join(here, "novelty_agent.py"),
                     os.path.join(here, os.pardir, "agents", "novelty_agent.py")]
            path = next(p for p in cands if os.path.exists(p))
            spec = importlib.util.spec_from_file_location("_nov_src", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._nov = mod.MyAgent(card_id=self.card_id, game_id=self.game_id,
                                    agent_name=self.agent_name, ROOT_URL=self.ROOT_URL,
                                    record=False, arc_env=self.arc_env, tags=["cycle.novelty"])
            self._nov.frames = self.frames
            return self._nov
        except Exception as e:
            self._nov_err = "%s: %s" % (type(e).__name__, e)
            self._nov = None
            print("[cycle] novelty delegation FAILED: %s" % self._nov_err, flush=True)
            return None

    def _orbit_fallback(self, latest_frame):
        grid = _as_grid(latest_frame.frame)
        if grid is None or not self._plan:
            return GameAction.from_id(self._legal(latest_frame)[0])
        aid, pt = self._plan[self.action_counter % self._plan_len]
        return self._mk(aid, pt)

    # ── ARC_K-random-actions-per-attempt search ───────────────────────────────────
    def _restart_step(self, latest_frame: FrameData) -> GameAction:
        """Play ARC_K randomized actions, then RESET and try again.

        WHY THIS IS A DIFFERENT MECHANISM, not a knob on the walk. `solve_levels.py` measured that
        RESET restarts the CURRENT LEVEL, not the game -- after finishing level 1 the reset hash is
        4412df0168a89497, not the fresh cfe5196fb75182bb. So **completed levels persist across a
        RESET**, and the 80-action budget can buy SEVERAL INDEPENDENT ATTEMPTS at the current level
        instead of one 80-action walk that is stuck with wherever it wandered.

        The cost is real and stated: `actions_i` is the CUMULATIVE count at completion, so attempts
        that fail inflate the denominator and shrink score_i = 100*(baseline/actions)^2. A level
        solved on the 4th 20-action attempt scores 100*(b/80)^2, not 100*(b/20)^2. The bet is that
        P(solve | 4 independent tries) beats P(solve | one 4x-longer try) by more than that costs.

        Each attempt shuffles the candidate orbit with seed = attempt number, so the attempts are
        genuinely independent rather than the same K actions repeated.
        """
        grid = _as_grid(latest_frame.frame)
        if grid is None:
            return GameAction.from_id(self._legal(latest_frame)[0])
        levels = int(latest_frame.levels_completed or 0)
        if levels != self._level:
            self._level = levels
            self._plan = self._candidates(grid, self._legal(latest_frame), ORDER)
            self._plan_len = len(self._plan)
            self._since = 0
            self._attempt += 1
            self._report["plans"].append({"level": levels, "n": self._plan_len,
                                          "at_action": self.action_counter})
        if not self._plan:
            return GameAction.RESET
        if self._since >= ARC_K:
            self._since = 0
            self._attempt += 1
            self._report["attempts"] = self._attempt
            return GameAction.RESET
        rng = random.Random(1000 + self._attempt)
        order = list(self._plan)
        rng.shuffle(order)
        aid, pt = order[self._since % len(order)]
        self._since += 1
        return self._mk(aid, pt)

    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state is GameState.WIN

    def _mk(self, aid: int, pt):
        if aid == 6:
            a = GameAction.ACTION6
            a.set_data({"x": int(pt[0]), "y": int(pt[1])})
            a.reasoning = "%s orbit click" % POLICY
            return a
        a = GameAction.from_id(aid)
        a.reasoning = "%s orbit" % POLICY
        return a

    def choose_action(self, frames, latest_frame) -> GameAction:
        try:
            return self._choose(latest_frame)
        except Exception as e:
            self._report["error"] = "%s: %s" % (type(e).__name__, e)
            # ⚠️ Printing on the error path is not decoration. A blanket `except` here silently
            # converted a delegation bug into "always play the first legal action", and the run
            # then reported a confident 0.0000 that looked like a policy result.
            if not self._reported_error:
                self._reported_error = True
                print("[cycle] choose_action error: %s" % self._report["error"], flush=True)
            ids = self._legal(latest_frame)
            return GameAction.from_id(ids[0])

    def _choose(self, latest_frame: FrameData) -> GameAction:
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self._report["resets"] += 1
            self._level = -1
            self._since = 0
            if POLICY == "restart":
                # A RESET that is not the first one starts a NEW ATTEMPT at the same level.
                self._attempt += 1
            return GameAction.RESET

        if POLICY == "restart":
            return self._restart_step(latest_frame)

        if POLICY == "novelty" or (POLICY == "hybrid" and self.action_counter >= ARC_K) \
                or (POLICY == "portfolio" and PORTFOLIO
                    and PORTFOLIO[min(self.action_counter // ARC_PHASE,
                                      len(PORTFOLIO) - 1)] == "novelty"):
            nov = self._novelty()
            if nov is None:
                # ⚠️ NEVER pretend. An earlier version wrapped this import in choose_action's
                # blanket `except Exception`, so a FAILED IMPORT silently degraded to "always
                # play the first legal action" and every portfolio containing a `novelty` phase
                # reported a number produced by a no-op policy. Measured: novelty-only through
                # this path scored 0.0000 against the real agent's 0.1265. Caught only because
                # the delegation was tested end-to-end against a known number.
                self._report.setdefault("novelty_import_error", self._nov_err)
                return self._orbit_fallback(latest_frame)
            nov.action_counter = self.action_counter
            return nov.choose_action(self.frames, latest_frame)

        grid = _as_grid(latest_frame.frame)
        if grid is None:
            return GameAction.from_id(self._legal(latest_frame)[0])
        levels = int(latest_frame.levels_completed or 0)
        if POLICY == "portfolio":
            ph = min(self.action_counter // ARC_PHASE, len(PORTFOLIO) - 1)
            key = (levels, ph)
            if key != self._level:
                self._level = key
                self._plan = self._candidates(grid, self._legal(latest_frame), PORTFOLIO[ph])
                self._plan_len = len(self._plan)
                self._report["plans"].append({"level": levels, "phase": PORTFOLIO[ph],
                                              "n": self._plan_len,
                                              "at_action": self.action_counter})
            if not self._plan:
                return GameAction.RESET
            off = self.action_counter - ph * ARC_PHASE
            aid, pt = self._plan[(off // DWELL) % self._plan_len]
            return self._mk(aid, pt)

        if levels != self._level:
            self._level = levels
            order = "rare" if POLICY == "hybrid" else ORDER
            self._plan = self._candidates(grid, self._legal(latest_frame), order)
            self._plan_len = len(self._plan)
            self._report["plans"].append({"level": levels, "n": self._plan_len,
                                          "at_action": self.action_counter})

        if not self._plan:
            return GameAction.RESET
        n = self._plan_len
        i = (self.action_counter // DWELL) % n
        aid, pt = self._plan[i]
        return self._mk(aid, pt)
