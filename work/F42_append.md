
---
## F42. ⭐⭐⭐ The complete public recipe: "The Duck" -- an LLM that writes Python, served by local vLLM

Written 2026-10-01. F41 found that the top teams run a local LLM inside the rerun; this is the recipe,
read out of the artifacts rather than inferred. **Every component is public and downloadable.**

### F42.1 What the solver is

`lordhansolo/taaf-kaggle-source` ships `src/ARC3-Inference/README.md`, whose first lines are:

> **# The Duck 🦆** — *the ARC3 inference harness in this repo: a **tool-using solver** that plays
> ARC-AGI-3 games through TAAF. It ties together: TAAF `Benchmark`/`GameAPI` execution; **a local
> OpenAI-compatible vLLM server**, or OpenRouter; **the duck's single `python` tool** with per-game
> saved modules; structured run artifacts for scoring, viewing, and trace export.*

The loop, from the same README: *"the solver gives the duck the latest game state, valid actions,
history, and a Python tool. **The duck inspects the board, writes small bits of code to reason about
it, and calls `action(...)` from inside Python to execute real game actions.**"* The observations it
reasons over are **structured, not pixels**:

* `current_frame.segmentation` -- connected components, object hashes, boundaries, containment,
  adjacency (the *preferred* view);
* `current_frame.ascii` -- a compact symbolic grid for small checks;
* `history`, `previous_frame`, `transitions`, `last_transition` -- before/after reasoning;
* `valid_actions`, and `last_action_result` with `changed_pixels`, `largest_changed_regions`,
  `level_completed`, `game_over`, `run_complete`.

⚠️ *"The raw numeric grid is intentionally hidden from the Python tool."* **That is F30's finding,
independently arrived at**: raw the frame is noise, semantic abstraction is what carries the game.

### F42.2 The model and the serving config

From the bundle's own `preamble.txt`:

```
benchmark.solver: HarnessSolver(label='duck-harness', model='local', analyzer_timeout=900.0,
                    max_runtime_s_per_game=3918.0, concurrency=14,
                    start_local_server=False, local_server_repo_dir='/app/ARC3-Inference')
benchmark.games : 25
git: ARC3-Inference          ca1bd02  clean  solution-improve-qwen38-flash-next
     tufa-arc-agi-framework  ca1bd02  clean  solution-improve-qwen38-flash-next
```

⇒ **the model is a Qwen3.8 variant ("Flash Next")**, matching the public family
`foysalemonshanto/lb-9-arc3-duck-v12-with-qwen-3-8-27b` (**LB-9**, Qwen 3.8 **27B**),
`keithtyser/duck-qwen3-8-flash-next-nvfp4-mtp`, `chiakazirim/duck-qwen3-8-tuned`,
`wuliao0/duck-qwen3-8-anim-base`. Serving, from the README: `server.max_model_len` **81,920** tokens,
`shared.context_window` **73,728**, `analyzer.target_context` **55,296** estimated input tokens,
**14 concurrent games**, and the Kaggle path is documented as *"model=local, 16 concurrent games,
75 minutes per game, and a 90-minute Kaggle"* budget.

### F42.3 Everything needed is public

| component | where | size |
|---|---|---|
| solver source + pickled benchmark | `lordhansolo/taaf-kaggle-source` (20 files: `benchmark_initial.pkl`, `setup_commands.json`, `src/ARC3-Inference/**`) | small |
| vLLM build for ARC-AGI-3 | `lordhansolo/vllm-main-e975732-arc3` (13 files, `apply_vllm_main_e975732_arc3.py` + layer blobs + `runtime-manifest.json`) | ~7 GB |
| the model | a Qwen3.8-Flash-Next dataset (to be identified) | ~15–55 GB depending on quantisation |
| the harness notebook | `lordhansolo/arc-agi-3-milestone-2` (rank 5, 23.84) | pulled |

⚠️ **The GPU quota is still the blocker**: `ENABLE_GPU = True`, a 27B-class model cannot run on CPU,
and the weekly quota is **0.00 h account-wide until 2026-10-03**. That is 2 days, against a deadline of
**2026-11-02**.

### F42.4 What this means for the project, stated once

**Our 0.18 is a floor produced by the absence of a language model, not by a limit of method.** Four
submissions built every generic mechanism this repo could invent -- a novelty walk, a portfolio of
candidate orderings, the official CNN baseline, and the baseline with its learner lifecycle changed --
and the ceiling was identical to the baseline every time. The top teams are 55–150× above that, and
**what they have that we do not is a model that reads a structured board description and writes code.**
The next action is not another policy; it is to reproduce the public stack.
