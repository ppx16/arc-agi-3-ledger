"""Build the hybrid agent: plan when the rules apply, delegate to StochasticGoose otherwise.

WHY A HYBRID AND NOT A CHOICE  (FINDINGS F22)
    Measured, both directions:
      * the planner solves LS20 level 1 in the BFS-proven optimal **13 actions**, but its own fallback
        is a novelty walk that scores **0 levels** locally;
      * the shipped StochasticGoose CNN scored **0.18** on the hidden set (rank 2346/3454), but it has
        no notion of any of the rules the planner derived.

    The competition rerun plays a HIDDEN game set, so on most games the rules will not apply and the
    fallback is what runs. Therefore **the fallback must be the thing that already scored 0.18**, not
    the novelty walk. Taking the planner instead of the CNN would trade a measured 0.18 for an
    unmeasured hope.

HOW IT IS ASSEMBLED (and why programmatically)
    `goose_agent.py` defines `class MyAgent(Agent)`. The hybrid renames it to `class _Goose(Agent)`
    and subclasses it, so the CNN's online learning, its sliding frame window and its coordinate head
    are inherited unchanged rather than copied. Renaming/copying by hand is exactly how the two halves
    would silently drift apart, so this builder asserts what it changes and refuses otherwise.

    Only `choose_action` is overridden:
        level changed  -> try to plan from the current frame
        plan exists    -> emit the next planned action
        otherwise      -> super().choose_action(...)   <- the CNN, untouched

Usage:
    D:\\python\\python.exe build_hybrid.py
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
AGENTS = ROOT / 'agents'
GOOSE = AGENTS / 'goose_agent.py'
PLANNER = AGENTS / 'planner_agent.py'
OUT = AGENTS / 'hybrid_agent.py'

MODEL_MARK = '# \u2500\u2500 the model \u2500'
AGENT_MARK = '# \u2500\u2500 the agent \u2500'

HYBRID_CLASS = '''

# \u2500\u2500 the hybrid \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
class MyAgent(_Goose):
    """Plan the level when the measured rules produce a plan; otherwise run the CNN unchanged.

    The CNN is inherited, not copied (see build_hybrid.py): `is_done`, `append_frame`, `MAX_ACTIONS`
    and the whole online learner come from `_Goose`, so the fallback is bit-for-bit the agent that
    scored 0.18 on the hidden set rather than a re-implementation of it.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._plan: list[int] = []
        self._at = 0
        self._plan_level = -1
        self.hybrid_report = {'planned_levels': 0, 'unplanned_levels': 0,
                              'planned_actions': 0, 'delegated_actions': 0}

    def _try_plan(self, frame: FrameData) -> None:
        """Build a plan for this level, or leave `self._plan` empty. Never raises.

        ⚠️ `unplanned_levels` counts EVERY level where no plan was produced, including the case where
        there is no block at all. The first version only counted the "found a block but no plan" case,
        so a game with no LS20-style block reported `unplanned_levels: 0` -- i.e. the counter was blind
        to the most common outcome, which is exactly the sort of reporting gap that makes a log say
        nothing happened when everything happened.
        """
        self._plan, self._at = [], 0
        try:
            g = _grid(frame)
            start = _find_block(g)
            if start is not None:
                acts = _plan_moves(g, start)
                if acts:
                    self._plan = acts
                    self.hybrid_report['planned_levels'] += 1
                    return
            self.hybrid_report['unplanned_levels'] += 1
        except Exception:
            self.hybrid_report['unplanned_levels'] += 1

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        lvl = int(latest_frame.levels_completed or 0)
        if lvl != self._plan_level:
            self._plan_level = lvl
            self._try_plan(latest_frame)

        if self._at < len(self._plan):
            aid = self._plan[self._at]
            self._at += 1
            self.hybrid_report['planned_actions'] += 1
            a = GameAction.from_id(aid)
            a.reasoning = {'why': 'planned', 'step': self._at, 'of': len(self._plan), 'level': lvl}
            return a

        # Delegate. Note this is the ONLY place the CNN is reached, so during a planned level its
        # online learner sees no transitions -- acceptable because a planned level needs no learning.
        self.hybrid_report['delegated_actions'] += 1
        return super().choose_action(frames, latest_frame)
'''


def main() -> int:
    goose = GOOSE.read_text(encoding='utf-8')
    planner = PLANNER.read_text(encoding='utf-8')

    # 1. the planner's model functions, verbatim, up to its agent section
    if AGENT_MARK not in planner:
        print('!! planner model/agent marker missing')
        return 2
    model = planner[:planner.index(AGENT_MARK)]
    # ⚠️ Strip the planner's MODULE DOCSTRING properly, not just its first line. Splitting off one
    # line left the rest of the prose as bare code and the syntax gate caught it -- which is exactly
    # what the gate is for, but the fix belongs here rather than in a hand-edit of the output.
    m = re.match(r'\s*"""(?:.|\n)*?"""\n', model)
    if m:
        model = model[m.end():]
    else:
        print('!! planner model does not start with a docstring -- check the layout')
        return 2
    # the planner's helper is called `_plan`; the hybrid calls it `_plan_moves` to avoid shadowing
    model, n = re.subn(r'\bdef _plan\(', 'def _plan_moves(', model)
    assert n == 1, 'expected exactly one `def _plan(` in the planner model, found %d' % n
    model, n2 = re.subn(r'\breturn _plan\(', 'return _plan_moves(', model)
    assert n2 <= 1

    # 2. rename the goose class so the hybrid can subclass it
    goose2, n3 = re.subn(r'^class MyAgent\(Agent\):', 'class _Goose(Agent):', goose, flags=re.M)
    assert n3 == 1, 'expected exactly one `class MyAgent(Agent):` in goose_agent.py, found %d' % n3
    # ⚠️ Do NOT run a second blanket rename here: the first substitution already renamed the class, so
    # `\bclass MyAgent\b` matches zero and an assert on it fails for a non-problem. What matters is
    # that nothing ELSE still refers to the old name -- a leftover `MyAgent` in the goose body (a
    # registry entry, a type hint, a string) would shadow or mis-register the hybrid. Assert on that
    # instead, and report where any survivors are.
    leftovers = [m.start() for m in re.finditer(r'\bMyAgent\b', goose2)]
    assert not leftovers, ('goose_agent.py still mentions MyAgent %d time(s) after the class rename '
                           '-- the hybrid class would collide; first at offset %d: %r'
                           % (len(leftovers), leftovers[0],
                              goose2[max(0, leftovers[0] - 60):leftovers[0] + 40]))

    header = (
        '"""ARC-AGI-3 submission agent: measured rules first, StochasticGoose otherwise.\n\n'
        'GENERATED by build_hybrid.py -- edit agents/planner_agent.py or agents/goose_agent.py and\n'
        're-run the builder. Do not hand-edit: the two halves would drift.\n\n'
        'Behaviour, measured:\n'
        '  * where the derived rules apply, it plans and spends actions only on execution -- LS20\n'
        '    level 1 is solved in the BFS-proven optimal 13 actions;\n'
        '  * everywhere else it is the StochasticGoose CNN, unchanged, which scored 0.18 on the\n'
        '    hidden set. The competition rerun uses a hidden game set, so the fallback is usually\n'
        '    what runs, and it must be the thing that already scored rather than the novelty walk.\n'
        '"""\n'
        'from __future__ import annotations\n\n'
    )
    # strip the planner's own future-import and docstring from the model block
    model = re.sub(r'^from __future__ import annotations\n', '', model, flags=re.M)
    model = re.sub(r'^from typing import Any\n', '', model, flags=re.M)
    model = re.sub(r'^from collections import deque\n', '', model, flags=re.M)
    model = re.sub(r'^import random\n', '', model, flags=re.M)
    model = re.sub(r'^import numpy as np\n', '', model, flags=re.M)
    model = re.sub(r'^from arcengine import.*\n', '', model, flags=re.M)
    model = re.sub(r'^from agents\.agent import Agent\n', '', model, flags=re.M)

    text = header + model.strip() + '\n\n\n' + goose2.rstrip() + '\n' + HYBRID_CLASS
    compile(text, str(OUT), 'exec')              # syntax gate before writing anything
    OUT.write_text(text, encoding='utf-8')
    print('built %s  (%d bytes)' % (OUT, len(text)))
    print('  planner model: %d chars   goose body: %d chars   hybrid class: %d chars'
          % (len(model), len(goose2), len(HYBRID_CLASS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
