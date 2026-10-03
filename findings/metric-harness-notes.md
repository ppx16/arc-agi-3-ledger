ARC-AGI-3: build an offline competition-metric harness, and measure that blind exploration is hopeless

Three things this turn, in order of how much they change the plan.

1. The rerun environment, read from the shipped notebook/framework rather than guessed:
   OPERATION_MODE=online, ENVIRONMENTS_DIR empty, ARC_BASE_URL=http://gateway:8001/.
   The hidden games run server-side, so there is no forked simulator to search, no game
   source to read, and no internet for an LLM. Three approach families are dead. (F23)

2. The competition metric IS computable offline. bench.py's docstring claimed the human
   baselines "are not public" -- FALSE. Every game ships metadata.json with
   baseline_actions, and Arcade.close_scorecard() in OFFLINE mode feeds the SHIPPED scorer
   from those same files. tools/score_local.py reuses that scorer instead of reimplementing
   it, so it prints the leaderboard number. Calibrated: the goose scores 0.00 locally,
   consistent with its 0.18 hidden -- so any local score above ~0 is a real gain. (F24)

3. The scoring arithmetic says LEVEL 1 IS THE WHOLE GAME: level 1 carries weight 1 of
   sum(1..L), so finishing it at human efficiency is worth 100/21..100/55 = 4.76..1.82 per
   game, ~3.1 across the 25 public games, against a top-10% cut of 3.80. (F25)

Then the measurement that matters. agents/novelty_agent.py is an explicit model-based
explorer (transition model keyed on the frame hash; prefer never-tried (state,action)
pairs, else least-visited successor; ACTION6 enumerated over component centroids;
deterministic per-state action ordering). Through the real scorer:

    goose     80 actions -> 0/25 games, 0.00
    novelty   80 actions -> 0/25 games, 0.00
    novelty 2000 actions -> 2/25 games, 0.15

Offline actions are free, so 25x the budget isolates the variable: the failure is
ALGORITHMIC, not budgetary. Blind exploration over raw-frame states does not solve these
games and tuning that family of rule will not fix it. (F26)

Also corrected: bench.py had never actually run the goose -- torch was missing from
starter/.venv, so --agent goose always died at import. Installed torch 2.14.0+cpu.

Added: tools/score_local.py (the metric), tools/probe_frame.py (frame format),
tools/trace_policy.py (per-action trace), agents/novelty_agent.py.
