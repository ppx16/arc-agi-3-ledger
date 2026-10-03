"""Keep the goose's learner ACROSS level boundaries instead of resetting it.

THE ARGUMENT, AND WHY IT IS A MECHANISM BET RATHER THAN A TUNED POLICY

    F37 proved local CV on the 25 public games is not a leaderboard proxy (a deterministic agent
    scored 0.2693 locally and 0.08 hidden), so nothing here may be chosen by a local score. It has to
    be justified by structure. There are two structural facts:

    1. ⭐⭐ **Scoring is PER LEVEL.** Measured through the shipped scorer (F38.2):
           r11l  total=81  level_actions=[27, 54, 0, ...]  level_scores=[66.4, 0, ...]
       27 + 54 = 81 and 100*(22/27)**2 = 66.4, so `actions_i` is the spend INSIDE level i. The
       weighted sum is `sum(score_i * i) / sum(i)`, so **level i counts i times** -- level 2 is worth
       exactly twice level 1, level 3 three times. THE SCORE IS IN THE LATER LEVELS.

    2. ⚠️ **The goose discards its entire learner at every level boundary.** `agents/goose_agent.py`
       lines 310-321, on every `levels_completed` change:

           self.experience_buffer.clear()
           self.experience_hashes.clear()
           self.action_model = ActionModel(...)          # a BRAND NEW, RANDOMLY INITIALISED CNN
           self.optimizer = optim.Adam(self.action_model.parameters(), lr=0.0001)

       So level 2 begins with a fresh random network, the same as level 1 did -- even though the
       levels of a game are the SAME GAME, harder, sharing its mechanics (click the coloured things,
       reach the target, ...). Every level pays the full learning cost again.

    ⇒ Those two facts point the same way. **Keeping the learner across the boundary should raise
    exactly the levels that carry the most weight.** That is the whole bet, and it is structural:
    it does not depend on any public game, and it cannot be overfitted to the public 25.

WHAT IS CHANGED, EXACTLY -- and nothing else

    The `clear()` calls and the model/optimizer recreation are removed. `prev_frame` and
    `prev_action_idx` are STILL reset to None, because across a level the frame changes completely
    and an (old_frame, action) -> new_frame transition would be a lie; we drop that one transition
    and keep everything learned before it.

    Nothing else in the agent is touched: same ActionModel, same reward (`frame_changed`), same
    `train_frequency`, same 4096-way coordinate head, same `MAX_ACTIONS = inf`, same sampling.

⚠️ STATED HONESTLY: this cannot be validated locally, because no local score predicts the hidden
   one. It is a bet on a mechanism, and it will be read from the leaderboard like the last three.

Usage:
    .venv\\Scripts\\python.exe score_local.py --agent ..\\agents\\goose_nolevel.py --games ls20,sp80
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "agents" / "goose_agent.py"
OUT = ROOT / "agents" / "goose_nolevel.py"

# the exact block to replace (whitespace-insensitive, matched as a whole)
OLD = re.compile(
    r"(\n\s*self\.experience_buffer\.clear\(\)\n"
    r"\s*self\.experience_hashes\.clear\(\)\n"
    r"\s*print\(\"Cleared experience buffer - new level reached\"\)\n"
    r"\s*\n"
    r"\s*# Reset network and optimizer for new level\n"
    r"\s*self\.action_model = ActionModel\(input_channels=self\.num_colours, grid_size=self\.grid_size\)\.to\(self\.device\)\n"
    r"\s*self\.optimizer = optim\.Adam\(self\.action_model\.parameters\(\), lr=0\.0001\)\n"
    r"\s*print\(\"Reset action model and optimizer for new level\"\)\n)",
    re.M,
)

NEW = """
                # ⭐ MECHANISM BET (F39): keep the learner across the level boundary.
                # Upstream clears the experience buffer and constructs a BRAND NEW randomly
                # initialised ActionModel + optimizer here, so every level re-pays the full
                # learning cost. Level i is worth i times level 1 in the score
                # (sum(score_i * i) / sum(i)), and a game's levels share its mechanics, so the
                # weights learned on level 1 are a warm start for level 2, not noise to discard.
                #
                # ⚠️ This block is ALSO the only place upstream ever constructs the model
                # (`__init__` sets self.action_model = None, line 153), so it must still build it
                # ONCE -- removing the construction outright left `self.action_model` as None and
                # every `choose_action` raised into the upstream crash handler.
                if self.action_model is None:
                    self.action_model = ActionModel(
                        input_channels=self.num_colours, grid_size=self.grid_size).to(self.device)
                    self.optimizer = optim.Adam(self.action_model.parameters(), lr=0.0001)
                    print("Built the action model (first level only)")
                else:
                    print("KEPT experience buffer and action model across the level boundary")
"""


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    out, n = OLD.subn(NEW, src, count=1)
    if n != 1:
        raise SystemExit("!! the level-reset block did not match exactly once (matched %d)" % n)
    header = (
        '"""StochasticGoose with the per-level learner reset REMOVED (see work/mk_goose_nolevel.py).\n\n'
        'Upstream: the official ARC-AGI-3 sample agent (Tufa Labs / Dries Smit), via the starter kit.\n'
        'Scored 0.18 on the hidden set as shipped; this differs from it in ONE respect -- the\n'
        'experience buffer, action model and optimizer survive a level change instead of being\n'
        'cleared and re-initialised. Rationale in FINDINGS F39.\n'
        '"""\n'
    )
    out = re.sub(r'^""".*?"""\n', header, out, count=1, flags=re.S)
    OUT.write_text(out, encoding="utf-8")
    compile(out, str(OUT), "exec")
    print("wrote %s (%d bytes, was %d)" % (OUT, len(out), len(src)))
    checks = [
        ("experience_buffer.clear()", 0),
        ("experience_hashes.clear()", 0),
        ("if self.action_model is None:", 1),
        ("self.action_model = ActionModel(", 1),
        ("KEPT experience buffer and action model", 1),
    ]
    bad = 0
    for probe, want in checks:
        got = out.count(probe)
        ok = got == want
        bad += 0 if ok else 1
        print("  %-44s count=%-3d expected=%-3d %s" % (probe, got, want, "OK" if ok else "!! FAIL"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
