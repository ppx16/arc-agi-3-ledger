"""Model-free scheduler simulator for the ARC-AGI-3 harness slot-priority question.

WHAT THIS IS
  A no-LLM, event-driven simulation of the harness's priority gate (`_PriorityGate`,
  `ARC3_MAX_ACTIVE_STREAMS=10`) over a fixed generated-token budget.  It answers one question:

      Under base vs dprime slot-priority, what is the expected final number of cleared levels?

  It is NOT a score predictor.  It abstracts away the model's decisions and keeps only what the
  scheduler actually touches: which game-run gets the next turn, and what state the priority
  function sees when a slot frees (level, actions, tokens, pace, total_levels, tail_fraction).

WHAT IT READS
  out/game_profiles.json  (produced by extract_profiles.py from the two benchmark.json Save runs)
    -> per game: number_of_levels, per-level actions-to-clear (observed medians, imputed where
       unobserved), tokens/turn, tokens/action, observed per-pass levels/tokens/turns.

MECHANICS MODELLED (taken from the real patch; see RULER.md "How the ruler actually runs")
  - token budget B = the one GPU's generated-token throughput x run duration.
  - 10 slots. A session holds a slot until it has spent a prefix quota P of generated tokens
    (the harness hands the slot over when the context is first trimmed); it then recomputes its
    priority and re-enters the queue, possibly winning the slot back immediately.
  - priority functions are copied verbatim in structure from the harness patch (cell 2) and the
    public dprime cell (cell 17), with the kernel's cell-4 env values.
  - waiting priorities are refreshed on every pump (tail fade phi recomputed), like
    `_PriorityGate._pump`.
  - never-started sessions: base = untrimmed band 2e6 - queue_position (outranks every trimmed
    game); dprime with PRICE_FRESH=1 = priced by the dprime formula at (1, 0, 0, pace=0).

POLICY VARIANTS (to decompose *why* a policy differs)
  base              : fresh band + harness formula      + fade 0.2  (what our submissions run)
  dprime            : priced fresh + dprime formula     + fade 0.4  (public 33.55 cell)
  dprime_band       : fresh band + dprime formula       + fade 0.4  (formula only)
  base_priced_fresh : priced fresh + harness formula    + fade 0.2  (fresh pricing only)

WHAT IT DOES NOT MODEL (stated as conditions in RULER.md)
  - the model's own behaviour (prompt/reasoning): per-level cost is a fixed recipe with lognormal
    jitter, not a model policy.  Cross-pass dispersion of observed outcomes is partly model
    behaviour and is NOT reproduced; the simulator is an allocation model, not a score model.
  - prefill/KV-cache costs of context switching, server batching effects, model startup;
  - infrastructure outages (handled as a separate, detectable failure mode upstream).

USAGE
  python sched_sim.py                    # full scenario suite -> out/sched_sim_results.{json,md}
  python sched_sim.py --seeds 40
  python sched_sim.py --validate-only    # leave-one-pass-out check of the cost model only
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import random
import statistics as st
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"D:\kaggle\arc")
EXP = ROOT / "exp"
OUT = EXP / "out"
PROFILES = OUT / "game_profiles.json"

# ---------------------------------------------------------------------------------------------
# real constants (harness patch cell 2 + dprime cell 17 + kernel cell 4 env)
# ---------------------------------------------------------------------------------------------
SCALE_DPRIME = 1000.0
TAIL_LOOKUP_REMAINING = {n: (8.0,) * (n - 3) + (7.0, 5.0, 0.0) for n in range(6, 11)}
DPRIME = {"level_pow": 0.5, "eff_const": 300.0, "eff_pow": 2.5, "pace_pow": 0.4,
          "pace_ref": 30000.0, "c_action": 0.1, "action_scale": 115.0, "c_token": 0.9,
          "token_scale": 225000.0, "lin_floor": 0.1, "rel_pow": 0.5,
          "b1": 10.0, "b2": 14.0, "b3": 16.0}
HUMAN_ACTIONS = 25.0        # ARC3_PRIORITY_HUMAN_ACTIONS default
ACTION_SCALE = 115.0        # ARC3_PRIORITY_ACTION_SCALE default
TOKEN_SCALE = 62000.0       # ARC3_PRIORITY_TOKEN_SCALE default
ACTION_WEIGHT = 0.25        # ARC3_PRIORITY_ACTION_WEIGHT default
FRESH_BAND = 2_000_000      # _PRIORITY_UNTRIMMED_BASE
BASE_FADE_FRAC = 0.2        # kernel cell 4: ARC3_PRIORITY_TAIL_FADE_FRACTION=0.2
DPRIME_FADE_FRAC = 0.4      # dprime cell: FADE default 0.4

POLICIES = {
    "base":              {"fresh_band": True,  "fn": "base",   "fade": BASE_FADE_FRAC},
    "base_priced_fresh": {"fresh_band": False, "fn": "base",   "fade": BASE_FADE_FRAC},
    "dprime":            {"fresh_band": False, "fn": "dprime", "fade": DPRIME_FADE_FRAC},
    "dprime_band":       {"fresh_band": True,  "fn": "dprime", "fade": DPRIME_FADE_FRAC},
    # not deployable as-is (needs the per-game difficulty recipe that the real scheduler does not
    # have): these show how much is available to a *well-designed* priority, given the same state.
    "greedy_next":       {"fresh_band": False, "fn": "greedy_next", "fade": BASE_FADE_FRAC},
    "greedy_game":       {"fresh_band": False, "fn": "greedy_game", "fade": BASE_FADE_FRAC},
}


def clamp_n(n):
    return min(10, max(6, int(n)))


def norm_levels(total_levels):
    n = clamp_n(total_levels)
    return 55.0 / (n * (n + 1) / 2), n


def base_priority(level, actions, tokens, pace, total_levels, phi):
    """Harness priority_value() under our kernel's env (normalize=1, tail_lookup='remaining',
    tail_fade=1, ARC3_PRIORITY_PACE=0 -> cost_multiplier=1.0)."""
    level = max(1, int(level))
    actions = max(0.0, float(actions))
    tokens = max(0.0, float(tokens))
    pace = min(2.0, max(0.5, float(pace)))
    norm, n = norm_levels(total_levels)
    current = level * (HUMAN_ACTIONS / (HUMAN_ACTIONS + actions)) ** 2 * norm
    tail = TAIL_LOOKUP_REMAINING[n][min(n, level) - 1] * phi
    chance = (ACTION_WEIGHT * 0.5 ** ((actions / ACTION_SCALE) ** 2)
              + (1.0 - ACTION_WEIGHT) * 0.5 ** ((tokens / (TOKEN_SCALE * pace)) ** 2))
    return max(1, int((current + tail) * chance / pace * 100.0))


def dprime_priority(level, actions, tokens, pace, total_levels, phi, p=DPRIME):
    """value_dprime() from the public dprime cell (returns int(v*1000))."""
    level = max(1, int(level))
    actions = max(0.0, float(actions))
    tokens = max(0.0, float(tokens))
    pace = max(0.0, float(pace))
    norm, n = norm_levels(total_levels)
    a = (1.0 + p["level_pow"] * (level - 1)) * norm \
        * (p["eff_const"] / (p["eff_const"] + actions)) ** p["eff_pow"]
    if pace > 0:
        a *= min(4.0, max(0.25, (p["pace_ref"] / max(1.0, pace)) ** p["pace_pow"]))
    rel = pace if pace > 0 else p["pace_ref"]
    scale = p["token_scale"] * (min(2.0, max(0.5, rel / p["pace_ref"])) ** p["rel_pow"])
    c = (p["c_action"] * max(p["lin_floor"], 1.0 - actions / p["action_scale"])
         + p["c_token"] * max(p["lin_floor"], 1.0 - tokens / scale))
    b = (0.0, p["b1"], p["b2"], p["b3"])[min(max(0, n - level), 3)]
    return max(1, int((a * c + b * phi) * SCALE_DPRIME))


PRIORITY_FN = {"base": base_priority, "dprime": dprime_priority}
# fixed per-policy RNG offsets: all policies must see the SAME per-session draw streams so the
# comparison is paired (delta variance is then the policy effect, not Monte-Carlo noise)
POL_SEED_OFFSET = {"base": 0, "base_priced_fresh": 1, "dprime": 2,
                   "dprime_band": 3, "greedy_next": 4, "greedy_game": 5}


# ---------------------------------------------------------------------------------------------
# game model
# ---------------------------------------------------------------------------------------------
@dataclass
class Game:
    name: str
    n_levels: int
    req_actions: list
    tokens_per_turn: float
    actions_per_turn: float
    tokens_per_action: float
    in_subset10: bool


def build_games(profiles):
    games = {}
    for name, p in profiles.items():
        games[name] = Game(
            name=name, n_levels=int(p["number_of_levels"]),
            req_actions=[float(x) for x in p["required_actions_list"]],
            tokens_per_turn=max(200.0, p["rates"]["tokens_per_turn"]),
            actions_per_turn=max(1.2, p["rates"]["actions_per_turn"]),
            tokens_per_action=max(50.0, p["rates"]["tokens_per_action"]),
            in_subset10=bool(p["in_subset10"]),
        )
    return games


# ---------------------------------------------------------------------------------------------
# one game-run / session
# ---------------------------------------------------------------------------------------------
SIGMA_TOKENS_TURN = 0.85      # lognormal sigma of generated tokens/turn (pooled observed log-sd 1.26;
                              # within-game smaller -> 0.85 compromise)
SIGMA_EFF_TURN = 0.25         # lognormal jitter of actions-per-token efficiency
SIGMA_REQ = 0.35              # per-attempt jitter on a level's action requirement


class Session:
    __slots__ = ("sidx", "game", "pass_idx", "rng", "log_tpt", "prefix_quota", "sigma_req",
                 "level", "levels_done", "a", "t", "tokens_total", "prefix_tokens",
                 "pace_n", "pace_tokens", "req", "done", "turn_tokens", "ever_active")

    def __init__(self, sidx, game, pass_idx, seed, prefix_quota, sigma_req):
        self.sidx = sidx
        self.game = game
        self.pass_idx = pass_idx
        self.rng = random.Random("%d:%d:%d" % (seed, sidx, pass_idx))
        self.log_tpt = math.log(game.tokens_per_turn)
        self.prefix_quota = prefix_quota
        self.sigma_req = sigma_req
        self.level = 1
        self.levels_done = 0
        self.a = 0.0
        self.t = 0.0
        self.tokens_total = 0.0
        self.prefix_tokens = 0.0
        self.pace_n = 0
        self.pace_tokens = 0.0
        self.req = self._draw_req()
        self.done = False
        self.turn_tokens = 0.0
        self.ever_active = False

    def _draw_req(self):
        g = self.game
        if self.level - 1 >= len(g.req_actions):
            return float("inf")
        return max(1.0, g.req_actions[self.level - 1]
                   * math.exp(self.sigma_req * self.rng.gauss(0.0, 1.0)))

    def do_turn(self):
        """One LLM turn: spend generated tokens, take actions, maybe clear levels.

        Actions are derived from this turn's tokens (actions ~ tokens / tokens_per_action)
        instead of an independent draw: the run-level tokens/action ratio is what the traces pin
        down, and independent draws bias E[tokens]/E[actions].
        """
        tok = math.exp(self.log_tpt + SIGMA_TOKENS_TURN * self.rng.gauss(0.0, 1.0))
        eff = math.exp(SIGMA_EFF_TURN * self.rng.gauss(0.0, 1.0))
        act = max(1, min(40, int(round(tok / self.game.tokens_per_action * eff))))
        self.turn_tokens = tok
        self.tokens_total += tok
        self.prefix_tokens += tok
        self.t += tok
        self.a += act
        g = self.game
        while not self.done and self.a >= self.req:
            self.a -= self.req
            self.levels_done += 1
            self.pace_n += 1
            self.pace_tokens += self.t
            self.level += 1
            self.t = 0.0
            if self.levels_done >= g.n_levels:
                self.done = True
                self.a = 0.0
                break
            self.req = self._draw_req()
        return tok

    def snapshot(self):
        pace = (self.pace_tokens / self.pace_n) if self.pace_n else 0.0
        return (self.level, self.a, self.t, pace, self.game.n_levels)


# ---------------------------------------------------------------------------------------------
# simulator
# ---------------------------------------------------------------------------------------------
@dataclass
class Scenario:
    name: str
    n_sessions: int
    games: list
    pass_of_session: list
    budget_tokens: float
    slots: int = 10
    prefix_scale: float = 1.0
    sigma_req: float = SIGMA_REQ


def simulate(policy, sc: Scenario, seed, prefix_pool):
    spec = POLICIES[policy]
    fn = PRIORITY_FN.get(spec["fn"])
    fade = spec["fade"]
    rng = random.Random(seed * 7919 + POL_SEED_OFFSET[policy])
    sessions = [
        Session(i, sc.games[i % len(sc.games)], sc.pass_of_session[i],
                seed * 17 + i,
                max(20000.0, rng.choice(prefix_pool) * sc.prefix_scale), sc.sigma_req)
        for i in range(sc.n_sessions)
    ]
    waiting = [[-1, seq, s, None, s.sidx * 100 + s.pass_idx] for seq, s in enumerate(sessions)]
    heapq.heapify(waiting)
    seq = len(waiting)
    active = []
    free = sc.slots
    spent = 0.0
    B = sc.budget_tokens
    turns_done = 0

    def phi_now():
        remaining = max(0.0, B - spent)
        window = fade * B
        return min(1.0, remaining / window) if window > 0 else 0.0

    def priority_of(item, phi):
        snap = item[3]
        g = item[2].game
        if snap is None:
            if spec["fresh_band"]:
                return FRESH_BAND - item[4]
            snap = (1, 0.0, 0.0, 0.0, g.n_levels)
        level, actions, tokens, pace, n_levels = snap
        if spec["fn"] == "base":
            return fn(level, actions, tokens, 1.0, n_levels, phi)
        if spec["fn"] == "dprime":
            return fn(level, actions, tokens, pace, n_levels, phi)
        # --- recipe-aware greedy (upper-reference, needs the difficulty recipe) ---
        req = g.req_actions
        li = min(len(req), max(1, int(level))) - 1
        next_left = max(1.0, req[li] - actions) if req else 1.0
        remaining_actions = next_left + sum(req[li + 1:])
        if spec["fn"] == "greedy_next":
            return max(1, int(1e9 / (next_left * g.tokens_per_action)))
        levels_left = max(1, int(n_levels) - int(level) + 1)
        return max(1, int(1e9 * levels_left / (remaining_actions * g.tokens_per_action)))

    def admit():
        nonlocal free
        if free <= 0 or not waiting:
            return False
        phi = phi_now()
        best_i, best_key = None, None
        for i, item in enumerate(waiting):       # _PriorityGate._pump re-prices every waiter
            pr = priority_of(item, phi)
            key = (-pr, item[1])
            if best_key is None or key < best_key:
                best_key, best_i = key, i
        item = waiting.pop(best_i)
        s = item[2]
        s.prefix_tokens = 0.0
        s.ever_active = True
        active.append(s)
        free -= 1
        return True

    while spent < B and (waiting or active):
        while free > 0 and waiting:
            if not admit():
                break
        if not active:
            break
        for s in active:                          # every active slot takes one turn
            s.do_turn()
            spent += s.turn_tokens
            turns_done += 1
            if spent >= B:
                break
        for s in list(active):
            if s.done:
                free += 1
                active.remove(s)
            elif s.prefix_tokens >= s.prefix_quota:   # context trim -> handover
                free += 1
                active.remove(s)
                heapq.heappush(waiting, [0, seq, s, s.snapshot(), 0])
                seq += 1
        if not active and not waiting:
            break

    levels = [s.levels_done for s in sessions]
    n_lv = [s.game.n_levels for s in sessions]
    return {
        "policy": policy,
        "total_levels": sum(levels),
        "score": 100.0 * sum(l / n for l, n in zip(levels, n_lv)) / len(sessions),
        "sessions_ever_active": sum(1 for s in sessions if s.ever_active),
        "sessions_never_started": sum(1 for s in sessions if not s.ever_active),
        "zero_level_sessions": sum(1 for l in levels if l == 0),
        "sessions_won": sum(1 for s in sessions if s.done),
        "turns": turns_done,
        "tokens_spent": spent,
        "levels_per_session": levels,
        "per_game": {g: [s.levels_done for s in sessions if s.game.name == g]
                     for g in {x.name for x in sc.games}},
    }


# ---------------------------------------------------------------------------------------------
# reference points
# ---------------------------------------------------------------------------------------------
def fair_reference(sc: Scenario):
    """Every session gets the same B/N token slice; levels from the recipe (no gate)."""
    per = sc.budget_tokens / sc.n_sessions
    total = 0
    for i in range(sc.n_sessions):
        g = sc.games[i % len(sc.games)]
        actions = per / g.tokens_per_action
        for req in g.req_actions:
            if actions >= req:
                actions -= req
                total += 1
            else:
                break
    return total


def oracle_upper_bound(sc: Scenario):
    """Cheapest-first marginal level over the whole budget; ignores the gate, so it upper-bounds
    what ANY allocation policy could reach."""
    heap = []
    for i in range(sc.n_sessions):
        g = sc.games[i % len(sc.games)]
        if g.req_actions:
            heapq.heappush(heap, (g.req_actions[0] * g.tokens_per_action, i, 0))
    spent, total = 0.0, 0
    while heap:
        cost, i, lvl = heapq.heappop(heap)
        if spent + cost > sc.budget_tokens:
            break
        spent += cost
        total += 1
        g = sc.games[i % len(sc.games)]
        if lvl + 1 < len(g.req_actions):
            heapq.heappush(heap, (g.req_actions[lvl + 1] * g.tokens_per_action, i, lvl + 1))
    return total


# ---------------------------------------------------------------------------------------------
# leave-one-pass-out validation of the cost model only (no scheduler)
# ---------------------------------------------------------------------------------------------
def loo_validate(profiles, n_seeds=15):
    rows = []
    global_ratios = [p["ratio_to_base_actions"] for p in profiles.values()
                     if p.get("ratio_to_base_actions")]
    global_ratio = st.median(global_ratios) if global_ratios else 1.0
    for name, p in profiles.items():
        n = p["number_of_levels"]
        base_apl = p["base_actions_per_level"] or []
        obs = p["observations"]
        if len(obs) < 2:
            continue
        for hold in obs:
            train = [o for o in obs if o is not hold]
            ratios = []
            for l in range(1, n + 1):
                acts = [o["per_level"][str(l)]["actions"] for o in train
                        if str(l) in o["per_level"]]
                if acts and l - 1 < len(base_apl) and base_apl[l - 1]:
                    ratios.append(st.median(acts) / base_apl[l - 1])
            ratio = st.median(ratios) if ratios else global_ratio
            req = []
            for l in range(1, n + 1):
                acts = [o["per_level"][str(l)]["actions"] for o in train
                        if str(l) in o["per_level"]]
                if acts:
                    req.append(st.median(acts))
                elif l - 1 < len(base_apl) and base_apl[l - 1]:
                    req.append(ratio * base_apl[l - 1])
                else:
                    req.append(120.0 * ratio)
            g = Game(name=name, n_levels=n, req_actions=[float(x) for x in req],
                     tokens_per_turn=max(200.0, p["rates"]["tokens_per_turn"]),
                     actions_per_turn=max(1.2, p["rates"]["actions_per_turn"]),
                     tokens_per_action=max(50.0, p["rates"]["tokens_per_action"]),
                     in_subset10=p["in_subset10"])
            preds = []
            for sd in range(n_seeds):
                s = Session(0, g, 0, sd + 1000 * sum(map(ord, name)), 1e18, SIGMA_REQ)
                while s.tokens_total < hold["tokens"] and not s.done:
                    s.do_turn()
                preds.append(s.levels_done)
            rows.append({"game": name, "run": hold["run"], "pass": hold["pass"],
                         "observed": hold["levels"], "predicted": st.mean(preds),
                         "turns": hold["turns"], "tokens": hold["tokens"]})
    if not rows:
        return {"n": 0}
    errs = [r["predicted"] - r["observed"] for r in rows]
    return {
        "n_observations": len(rows),
        "bias": round(st.mean(errs), 3),
        "mae": round(st.mean(abs(e) for e in errs), 3),
        "rmse": round(math.sqrt(st.mean(e * e for e in errs)), 3),
        "corr": round(st.correlation([r["predicted"] for r in rows],
                                     [r["observed"] for r in rows]), 3),
        "observed_total": sum(r["observed"] for r in rows),
        "predicted_total": round(sum(r["predicted"] for r in rows), 1),
        "rows": rows,
    }


# ---------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------
def load_profiles():
    d = json.load(open(PROFILES, encoding="utf-8"))
    return d["profiles"], d["meta"]


def prefix_pool_from_observations(profiles):
    """Prefix token quota = generated tokens of game-runs that ran until handover/deadline
    (state == 'gave_up', no analyzer-failure note).  Won runs stop early and are censored."""
    pool = [float(o["tokens"]) for p in profiles.values() for o in p["observations"]
            if o["state"] == "gave_up" and "analyzer failed" not in str(o.get("note") or "")
            and o["tokens"] > 5000]
    return pool or [150000.0]


def make_scenarios(games25, pool):
    names = list(games25)
    B_online = 19.7e6

    def online_sessions(seed=11):
        rng = random.Random(seed)
        return [games25[names[rng.randrange(len(names))]] for _ in range(110)]

    sc = []
    for tag, B in [("online_B19.7M", B_online), ("online_B15M", 15.0e6),
                   ("online_B25M", 25.0e6)]:
        sc.append(Scenario(name=tag, n_sessions=110, games=online_sessions(),
                           pass_of_session=[0] * 110, budget_tokens=B, slots=10))
    for tag, scale in [("online_prefix0.75", 0.75), ("online_prefix1.25", 1.25)]:
        sc.append(Scenario(name=tag, n_sessions=110, games=online_sessions(),
                           pass_of_session=[0] * 110, budget_tokens=B_online, slots=10,
                           prefix_scale=scale))
    for tag, sigma in [("online_sigreq0.15", 0.15), ("online_sigreq0.60", 0.60)]:
        sc.append(Scenario(name=tag, n_sessions=110, games=online_sessions(),
                           pass_of_session=[0] * 110, budget_tokens=B_online, slots=10,
                           sigma_req=sigma))
    games100, passes = [], []
    for p in range(4):
        for g in names:
            games100.append(games25[g])
            passes.append(p)
    sc.append(Scenario(name="offline_local_25x4", n_sessions=100, games=games100,
                       pass_of_session=passes, budget_tokens=17.9e6, slots=10))
    # the public 33.55 notebook's demo ruler (verbatim cell 16): demo_excluded_games = the 15
    # hard games, n_passes=1, and the demo branch hardcodes max_runtime_s_per_game = 25*60.
    # 10 concurrent sessions at the observed 617 generated tok/s for 1500 s = 0.93M tokens.
    sub10 = ["ar25", "ft09", "lp85", "r11l", "re86", "sb26", "sc25", "tr87", "tu93", "vc33"]
    sc.append(Scenario(name="public_style_10x1_25min", n_sessions=10,
                       games=[games25[g] for g in sub10], pass_of_session=[0] * 10,
                       budget_tokens=0.93e6, slots=10))
    sc.append(Scenario(name="public_style_10x1_50min", n_sessions=10,
                       games=[games25[g] for g in sub10], pass_of_session=[0] * 10,
                       budget_tokens=1.85e6, slots=10))
    return sc


def ensemble(sc, seeds, pool):
    rows = {p: [] for p in POLICIES}
    metrics = {p: [] for p in POLICIES}
    for sd in range(seeds):
        for pol in POLICIES:
            r = simulate(pol, sc, sd, pool)
            rows[pol].append(r["total_levels"])
            metrics[pol].append(r)
    base = rows["base"]
    out = {"scenario": sc.name, "n_sessions": sc.n_sessions,
           "budget_tokens": sc.budget_tokens, "slots": sc.slots,
           "prefix_scale": sc.prefix_scale, "sigma_req": sc.sigma_req,
           "results": {}, "fair_reference_total_levels": fair_reference(sc),
           "oracle_total_levels": oracle_upper_bound(sc), "seeds": seeds}
    for pol in POLICIES:
        tot = rows[pol]
        met = metrics[pol]
        out["results"][pol] = {
            "total_mean": round(st.mean(tot), 2),
            "total_sd": round(st.pstdev(tot), 2),
            "delta_vs_base": round(st.mean(tot) - st.mean(base), 2),
            "delta_sd_paired": round(st.stdev([a - b for a, b in zip(tot, base)]), 2)
            if len(base) > 1 else 0.0,
            "p_better_than_base": round(sum(1 for a, b in zip(tot, base) if a > b) / len(base), 3),
            "score_mean": round(st.mean([m["score"] for m in met]), 2),
            "score_sd": round(st.pstdev([m["score"] for m in met]), 2),
            "sessions_ever_active": round(st.mean([m["sessions_ever_active"] for m in met]), 1),
            "sessions_never_started": round(st.mean([m["sessions_never_started"] for m in met]), 1),
            "zero_level_sessions": round(st.mean([m["zero_level_sessions"] for m in met]), 1),
            "sessions_won": round(st.mean([m["sessions_won"] for m in met]), 1),
        }
        per_game_mean = {}
        for g in {x.name for x in sc.games}:
            vals = [x for m in met for x in m["per_game"].get(g, [])]
            per_game_mean[g] = round(st.mean(vals), 2) if vals else None
        out["results"][pol]["per_game_levels"] = per_game_mean
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    profiles, pmeta = load_profiles()
    games25 = build_games(profiles)
    pool = prefix_pool_from_observations(profiles)
    print("games: %d | prefix-quota pool: n=%d median=%.0f mean=%.0f"
          % (len(games25), len(pool), st.median(pool), st.mean(pool)))

    val = loo_validate(profiles)
    print("LOO cost-model validation: n=%d bias=%+.2f MAE=%.2f RMSE=%.2f corr=%.3f "
          "obs_total=%.0f pred_total=%.1f"
          % (val["n_observations"], val["bias"], val["mae"], val["rmse"], val["corr"],
             val["observed_total"], val["predicted_total"]))
    (OUT / "cost_model_validation.json").write_text(
        json.dumps(val, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.validate_only:
        return

    scenarios = make_scenarios(games25, pool)
    results = []
    for sc in scenarios:
        seeds = args.seeds if sc.name in ("online_B19.7M", "offline_local_25x4") \
            else max(20, args.seeds // 2)
        r = ensemble(sc, seeds, pool)
        results.append(r)
        b = r["results"]["base"]
        print("%-20s base=%6.1f | dprime=%6.1f (%+.1f) | dprime_band=%6.1f | "
              "base_priced=%6.1f | greedy_next=%6.1f | greedy_game=%6.1f | oracle=%d | "
              "started(base)=%.0f"
              % (sc.name, b["total_mean"], r["results"]["dprime"]["total_mean"],
                 r["results"]["dprime"]["delta_vs_base"],
                 r["results"]["dprime_band"]["total_mean"],
                 r["results"]["base_priced_fresh"]["total_mean"],
                 r["results"]["greedy_next"]["total_mean"],
                 r["results"]["greedy_game"]["total_mean"],
                 r["oracle_total_levels"], b["sessions_ever_active"]))
        if sc.name.startswith("public_style"):
            print("    -> ruler reading (subset score): mean=%.2f sd=%.2f over %d seeds"
                  % (b["score_mean"], b["score_sd"], r["seeds"]))

    payload = {"meta": {
        "source_profiles": str(PROFILES),
        "profile_meta": pmeta,
        "prefix_pool_n": len(pool),
        "prefix_pool_median": st.median(pool),
        "prefix_pool_mean": st.mean(pool),
        "budget_basis": "online: 617 generated tok/s (17.9M tokens / 29018 s observed) x 31920 s "
                        "= 19.7M; offline_local: 17.9M observed for the 8.05 h 100-run pass",
        "policies": POLICIES,
        "mechanics": {"slots": 10, "sigma_tokens_turn": SIGMA_TOKENS_TURN,
                      "sigma_eff_turn": SIGMA_EFF_TURN, "sigma_req": SIGMA_REQ},
        "cost_model_validation": val}, "scenarios": results}
    (OUT / "sched_sim_results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Scheduler simulator results (no LLM; budget in generated tokens; 10 slots)", "",
         "delta is dprime minus base, paired over seeds. `dprime_band` = dprime formula but "
         "fresh games keep the top band; `base_priced_fresh` = base formula but fresh games are "
         "priced; `greedy_*` = recipe-aware upper references (not deployable: they need the "
         "per-game difficulty recipe). Oracle = cheapest-first allocation of the same budget.",
         "",
         "| scenario | base | dprime | delta | dprime_band | base_priced_fresh | greedy_next | "
         "greedy_game | oracle | started (base) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        rs = r["results"]
        L.append("| %s | %.1f | %.1f | %+.1f | %.1f | %.1f | %.1f | %.1f | %d | %.0f/%d |"
                 % (r["scenario"], rs["base"]["total_mean"], rs["dprime"]["total_mean"],
                    rs["dprime"]["delta_vs_base"], rs["dprime_band"]["total_mean"],
                    rs["base_priced_fresh"]["total_mean"], rs["greedy_next"]["total_mean"],
                    rs["greedy_game"]["total_mean"], r["oracle_total_levels"],
                    rs["base"]["sessions_ever_active"], r["n_sessions"]))
    L += ["", "## zero-level sessions / never started", "",
          "| scenario | base zero | dprime zero | base never-started | dprime never-started |",
          "|---|---|---|---|---|"]
    for r in results:
        rs = r["results"]
        L.append("| %s | %.1f | %.1f | %.1f | %.1f |"
                 % (r["scenario"], rs["base"]["zero_level_sessions"],
                    rs["dprime"]["zero_level_sessions"],
                    rs["base"]["sessions_never_started"],
                    rs["dprime"]["sessions_never_started"]))
    L += ["", "## simulated repeatability of the public-style 10-game x 1-pass ruler", "",
          "Same-config reruns in the simulator; sd is the seed-to-seed sd of the subset-10 score "
          "(points). This is the best available estimate of that ruler's noise without running it.",
          "", "| scenario | subset score mean | subset score sd | 2x2sd MDE (points) |",
          "|---|---|---|---|"]
    for r in results:
        if r["scenario"].startswith("public_style"):
            b = r["results"]["base"]
            L.append("| %s | %.2f | %.2f | %.1f |"
                     % (r["scenario"], b["score_mean"], b["score_sd"], 2 * math.sqrt(2) * b["score_sd"]))
    (OUT / "sched_sim_results.md").write_text("\n".join(L), encoding="utf-8")
    print("\nwrote", OUT / "sched_sim_results.json", "and sched_sim_results.md")


if __name__ == "__main__":
    main()
