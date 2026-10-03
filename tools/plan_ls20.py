"""LS20 planner: derive the lattice and the passability rule from the FRAME ALONE, no engine calls.

THE RULE, MEASURED (cell_signature.py)
    Take the 5x5 footprint at each lattice cell (lattice = 5-pixel steps anchored at the block's
    start). Then:

        footprint is uniformly colour 3 (wall)   -> PASSABLE   (33 of 33 such cells were reachable)
        footprint is uniformly colour 4 (background) -> BLOCKED (0 of 18 such cells were reachable)

    The inversion is the whole trick, and it is why guessing was hopeless: in LS20 the drawn WALL is
    the corridor and the open background is void.

WHY A PLANNER AND NOT A SEARCH (FINDINGS F5)
    RHAE is `(human_actions / ai_actions) ** 2` per level, capped at 1.15. BFS to solve level 1 cost
    1777 env steps against a budget of 80 actions per game, so a searching agent cannot score. The
    graph is a pure function of the frame, so it can be built and searched in the agent's head at
    zero action cost.

WHAT THIS SCRIPT IS FOR
    Verification, not submission: it recomputes the graph from the frame and compares it cell-for-cell
    against the graph the engine actually produced. A planner is only trustworthy when it reproduces
    the ground truth exactly.

Usage:
    .venv\\Scripts\\python.exe plan_ls20.py --game ls20
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "starter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
import os as _os_for_dirs
_os_for_dirs.environ.setdefault("ENVIRONMENTS_DIR", str(ROOT / "environment_files"))
_os_for_dirs.environ.setdefault("RECORDINGS_DIR", str(ROOT / "recordings"))

import numpy as np                                        # noqa: E402
import arc_agi                                            # noqa: E402
from arc_agi import OperationMode                         # noqa: E402
from arcengine import GameAction, GameState               # noqa: E402

WALL, BG = 3, 4
MOVES = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def frame_of(obs):
    a = np.asarray(obs.frame)
    return (a[-1] if a.ndim == 3 else a).astype(np.uint8)


def find_block(g, top=12, bottom=9, w=5, htop=2, hbot=3):
    H, W = g.shape
    for r in range(H - (htop + hbot) + 1):
        for c in range(W - w + 1):
            if np.all(g[r:r + htop, c:c + w] == top) and np.all(g[r + htop:r + htop + hbot, c:c + w] == bottom):
                return r, c
    return None


def passable(g, r, c, start=None, wall_min=20):
    """The measured rule, as a THRESHOLD plus one exception.

    `cell_signature.py` first suggested "footprint uniformly WALL". That had zero false positives but
    missed two cells:
        (15,34) = {3:20, 5:5}        the shaft up into the top panel
        (30,19) = {0:3, 1:2, 3:20}   a cell containing the 2-pixel `.` object
    Both have exactly 20 of 25 pixels equal to WALL and none with fewer was ever reachable, so the
    rule is `wall_count >= 20`.

    ⚠️ The one exception is the START cell. Its footprint holds the BLOCK (colours 9 and 12), so the
    threshold rejects it -- yet three engine edges move into it. Vacating a cell paints it as wall, so
    the block can always step back onto its own trail. Treating the block's own cell as passable is
    what closes the last 3 of 144 edges.
    """
    if start is not None and (r, c) == start:
        return True
    if not (0 <= r <= g.shape[0] - 5 and 0 <= c <= g.shape[1] - 5):
        return False
    blk = g[r:r + 5, c:c + 5]
    return int((blk == WALL).sum()) >= wall_min


def build_graph(g, start, limit=12):
    """Every lattice cell within `limit` steps of the start that the rule calls passable."""
    graph = {}
    q = deque([(start, 0)])
    seen = {start}
    while q:
        (r, c), d = q.popleft()
        outs = {}
        for aid, (dr, dc) in MOVES.items():
            nr, nc = r + dr * 5, c + dc * 5
            if passable(g, nr, nc, start):
                outs[aid] = (nr, nc)
                if (nr, nc) not in seen and d + 1 <= limit:
                    seen.add((nr, nc))
                    q.append(((nr, nc), d + 1))
        graph[(r, c)] = outs
    return graph


def find_goal(g, start, wall_min=20):
    """The goal: the UNIQUE lattice cell lying fully inside a colour-5 region enclosed by colour 3.

    Measured, and it is unique on LS20's level 1. There is exactly one enclosed colour-5 box
    (rows 9-15, cols 33-39) and exactly one lattice cell fully inside it: (10,34) -- which is the
    cell whose upward move completed the level.

    ⚠️ The bottom-left panel (rows 53-62, cols 1-10) looks like the top one but is correctly NOT
    matched: its rim is background, not colour 3, so the enclosure test excludes it. That is the
    difference between a goal marker and a legend.
    """
    from collections import deque
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    boxes = []
    for r in range(H):
        for c in range(W):
            if g[r, c] != 5 or seen[r, c]:
                continue
            q, comp = deque([(r, c)]), []
            seen[r, c] = True
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
            r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
            ring = []
            if r0 - 1 >= 0:
                ring += [g[r0 - 1, x] for x in range(c0, c1 + 1)]
            if r1 + 1 < H:
                ring += [g[r1 + 1, x] for x in range(c0, c1 + 1)]
            if c0 - 1 >= 0:
                ring += [g[y, c0 - 1] for y in range(r0, r1 + 1)]
            if c1 + 1 < W:
                ring += [g[y, c1 + 1] for y in range(r0, r1 + 1)]
            if ring and len(comp) >= 9 and all(v == WALL for v in ring):
                boxes.append((r0, r1, c0, c1))
    targets = []
    # ⚠️ Only LATTICE cells can be goals. The lattice is anchored at the block's start, so its
    # coordinates are start+5k -- NOT every (r, c). Scanning all positions found NINE cells inside
    # the 7x7 panel interior (rows 9-15, cols 33-39), none of them on the lattice, so the BFS had no
    # reachable target and returned no plan at all. Restricting to lattice offsets leaves exactly one.
    rows = [start[0] + 5 * k for k in range(-12, 13) if 0 <= start[0] + 5 * k <= H - 5]
    cols = [start[1] + 5 * k for k in range(-12, 13) if 0 <= start[1] + 5 * k <= W - 5]
    for r in rows:
        for c in cols:
            if (r, c) == start:
                continue
            for (r0, r1, c0, c1) in boxes:
                if r >= r0 and r + 4 <= r1 and c >= c0 and c + 4 <= c1:
                    targets.append((r, c))
                    break
    return targets


def find_collectibles(g, start, wall_min=20, object_colours=(1,)):
    """Collectibles: lattice cells containing a pixel of the OBJECT colour.

    ⚠️ Two earlier versions of this function were wrong, and both were wrong the same way -- they
    inferred "object" from the FOOTPRINT's colour mix instead of from the object itself:

      v1: `20 <= wall < 25`                 caught (15,34), whose 5 colour-5 pixels are the PANEL's
                                            bottom row on the footprint border -- not an object.
      v2: v1 + "non-wall pixels must be     fixed level 1, but on level 2 returned (45,49) instead
          interior"                          of the true (45,19), and one spurious pickup derails
                                            the whole plan because `plan` requires them all.

    The evidence that settles it is the colour census. Both levels contain EXACTLY TWO pixels of
    colour 1 -- the `.` object -- and nothing else of that colour:

      level 1  colour 1 at (32,20),(33,21)  ->  lattice cell (30,19)   [the true pickup]
      level 2  colour 1 at (47,22),(48,23)  ->  lattice cell (45,19)   [the true pickup]

    So the object is identified by ITS OWN colour, not by what the footprint happens to contain.
    `object_colours` is a parameter because this is evidence from two levels, not a law; if a later
    level uses another colour, the detector must be widened deliberately rather than by guess.
    """
    H, W = g.shape
    mask = np.isin(g, list(object_colours))
    if not mask.any():
        return []
    out = []
    rows = [start[0] + 5 * k for k in range(-12, 13)]
    cols = [start[1] + 5 * k for k in range(-12, 13)]
    for r in rows:
        for c in cols:
            if (r, c) == start or not (0 <= r <= H - 5 and 0 <= c <= W - 5):
                continue
            if mask[r:r + 5, c:c + 5].any():
                out.append((r, c))
    return out


def plan(g, start, wall_min=20):
    """BFS on the rule-derived graph. Collectibles must be taken before the goal opens.

    State is (cell, frozenset(collected)) -- NOT the cell alone. F15 is the reason: two routes reach
    the same cell and behave differently, because one took the pickup. A position-only search emits a
    7-action plan the engine refuses.
    """
    goals = set(find_goal(g, start, wall_min))
    pickups = set(find_collectibles(g, start, wall_min))
    if not goals:
        return None, None, pickups
    q = deque([(start, frozenset(), [])])
    seen = {(start, frozenset())}
    while q:
        (r, c), got, path = q.popleft()
        if (r, c) in goals and path and pickups <= got:
            return path, (r, c), pickups
        for aid, (dr, dc) in MOVES.items():
            nr, nc = r + dr * 5, c + dc * 5
            if not (0 <= nr <= g.shape[0] - 5 and 0 <= nc <= g.shape[1] - 5):
                continue
            # the goal cell is enterable by definition even though the wall rule rejects it
            if not (passable(g, nr, nc, start, wall_min) or (nr, nc) in goals):
                continue
            ngot = got | ({(nr, nc)} if (nr, nc) in pickups else set())
            st = ((nr, nc), ngot)
            if st in seen:
                continue
            seen.add(st)
            q.append(((nr, nc), ngot, path + [aid]))
    return None, None, pickups


def measure_graph(arc, game, max_nodes=900):
    """Ground truth: walk the engine and record the real edges."""
    env = arc.make(game)
    env.step(GameAction.RESET)
    g0 = frame_of(env.observation_space)
    start = find_block(g0)

    def goto(path):
        env.step(GameAction.RESET)
        for aid in path:
            env.step(GameAction.from_id(aid))
        return frame_of(env.observation_space)

    real, seen, q, nodes = {}, {start}, deque([(start, [])]), 0
    while q and nodes < max_nodes:
        pos, path = q.popleft()
        real.setdefault(pos, {})
        for aid in MOVES:
            goto(path)
            env.step(GameAction.from_id(aid))
            o = env.observation_space
            nodes += 1
            nb = find_block(frame_of(o))
            if nb is None or nb == pos:
                continue
            real[pos][aid] = nb
            if int(o.levels_completed or 0) > 0 or o.state is GameState.GAME_OVER:
                continue
            if nb not in seen:
                seen.add(nb)
                q.append((nb, path + [aid]))
    return g0, start, real, seen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--max-nodes", type=int, default=900)
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    g0, start, real, seen = measure_graph(arc, a.game, a.max_nodes)
    pred = build_graph(g0, start)

    print("block start %s | background %d" % (start, int(np.bincount(g0.ravel()).argmax())))
    print("engine reachable cells : %d" % len(seen))
    print("rule-predicted cells   : %d" % len(pred))
    print()

    only_real = sorted(seen - set(pred))
    only_pred = sorted(set(pred) - seen)
    print("⚠️ reachable but NOT predicted : %s" % (only_real or "none"))
    print("⚠️ predicted but NOT reachable : %s" % (only_pred or "none"))
    print()

    # edge-level agreement
    mism = []
    for pos in sorted(real):
        r_pred = pred.get(pos, {})
        r_real = real[pos]
        for aid in MOVES:
            p, q_ = r_pred.get(aid), r_real.get(aid)
            if p != q_:
                mism.append((pos, aid, q_, p))
    print("edge mismatches: %d" % len(mism))
    for pos, aid, got, want in mism[:15]:
        print("   cell %s ACTION%d : engine->%s  rule->%s" % (pos, aid, got, want))

    agree = 1.0 - len(mism) / max(1, len(real) * 4)
    print()
    print("AGREEMENT: %.3f of %d edges" % (agree, len(real) * 4))

    # ── END-TO-END: plan from the FRAME ALONE, then replay on the engine ──────────────
    # This is the test that matters. Everything above compares graphs; this asks whether the plan
    # the rule produces actually completes the level, and whether it matches the BFS optimum of 13.
    print()
    print("=== end-to-end: plan from pixels, then execute ===")
    goals = find_goal(g0, start)
    print("goal cells found from the frame: %s" % (goals or "NONE"))
    actions, goal, pickups = plan(g0, start)
    print("collectibles found from the frame: %s" % (sorted(pickups) or "none"))
    print("planned actions: %s  (%d actions)  goal=%s"
          % ("".join(str(x) for x in actions) if actions else "-",
             len(actions) if actions else 0, goal))
    if actions:
        env = arc.make(a.game)
        env.step(GameAction.RESET)
        for aid in actions:
            env.step(GameAction.from_id(aid))
        o = env.observation_space
        print("after replaying them: state=%s levels_completed=%s" % (o.state, o.levels_completed))
        print("⇒ %s" % ("PLAN WORKS — the level completed" if int(o.levels_completed or 0) > 0
                        else "PLAN FAILED — the level did NOT complete"))


if __name__ == "__main__":
    main()
