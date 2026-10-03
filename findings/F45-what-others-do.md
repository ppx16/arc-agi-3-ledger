# F45. What everyone else is actually doing on ARC-AGI-3 — surveyed, not assumed

Surveyed **200 public kernels** for `arc-prize-2026-arc-agi-3` via the API, classified by name family,
then pulled `kernel-metadata.json` for the ones that are **not** Duck-named to see what they mount and
what hardware they ask for.

## 1. The ecosystem is one method, by a wide margin

| family | kernels |
|---|---|
| **DUCK harness (TAAF)** | **92** |
| **Qwen3.8 / flash-next** | **55** |
| TAAF (non-Duck naming) | 33 |
| eval / harness / probe | 27 |
| thui variants | 13 |
| milestone-2 (dfranzen / richardcsaky lineage) | 11 |
| world-model / neural | 6 |
| agent (generic naming) | 6 |
| baseline / starter | 5 |
| (none of the above) | 44 |

⇒ **Roughly half of all public kernels are the TAAF Duck harness by name**, and most of the rest are
that harness with a different model swapped in. There is no meaningful second method with a score.

## 2. ⚠️ Every scoring entry asks for the SAME GPU — `NvidiaRtxPro6000`

Pulled the metadata of the eight most interesting **non-Duck** notebooks. Every one that uses a model
requests Blackwell:

| notebook | `machine_shape` | model(s) mounted |
|---|---|---|
| `amanatar/arc-agi-3-hybrid-repl-agent` | **NvidiaRtxPro6000** | `keithtyser/qwen3-8-flash-next-nvfp4` |
| `bang1850/arc-prize-2026-sovereign-agent` | **NvidiaRtxPro6000** | 2 × `dfranzen/qwen3.8-flash-next-*` + a MoE |
| `iamjasonfeng/chimpanzee-1-1-eval` | **NvidiaRtxPro6000** | — (2 private datasets) |
| **`mbmmurad/arc-agi-3-lb-0-86-3rd-place-candidate-milestone`** | **NvidiaRtxPro6000** | **`google/gemma-4/Transformers/gemma-4-31b-it/1`** |
| `nihilisticneuralnet/arc-agi-3-retained-reasoning` | **NvidiaRtxPro6000** | `keithtyser/qwen3-8-flash-next-nvfp4` |
| `huikang/`**`milestone-1`**`-4th-place` | **gpu=False** | none |
| `ruichardliu/`**`milestone1`**`-2nd-solution` | **gpu=False** | gemma-4-31b (listed, unused without a GPU) |

So the hardware gate is **not a quirk of the Duck recipe** — it is the norm. The only GPU-free
notebooks in the sample are **Milestone 1** artifacts, i.e. a *different phase* of the competition.

Hardware-gating is visible even in kernel names: `…observed-probe-memory-RTX6000`,
`face-of-agi-arc-agi-3-RTX6000`.

## 3. The model families in play
* **Qwen3.8 "Flash Next"** in several quantisations — NVFP4 (`keithtyser`, `nvidia`, `xiao...`),
  W4A16 AutoRound (`dfranzen/intel-…`, `woochangsim/…`), GPTQ (`josephayanda/…`, `ram2121/…`),
  REAP-pruned (`boristown/…-reap-448e`), and FP8 (`foysalemonshanto/…-fp8-repacked-v1`).
* **`google/gemma-4-31b-it`** — used by two notebooks, including the one named "LB 0.86 3rd place
  candidate".
* A private MoE (`bang1850/qwen3-5-dark-genius-moe-sovereign`).

⚠️ All of the above are ≥27B class or bigger. **Nothing in the sample runs a small model**, which is
consistent with F42.4: the score comes from a model that reads a structured board and writes code.

## 4. What this settles for us

1. **There is no public ARC-AGI-3 method that scores without Blackwell-class hardware.** We measured
   that our account is handed **2× Tesla T4 (cc 7.5)** no matter what `machine_shape` says (F43/F44).
   So this is not "we picked the wrong method" — **the whole public frontier is behind a hardware wall
   we cannot climb.**
2. **The GPU-free public work is Milestone 1**, a different phase, so it does not transfer.
3. **The one variant not yet tested is the non-vLLM path** — the TAAF bundle ships
   `configs/inference.local.llama.json`, so the harness has a llama.cpp backend, and GGUF Q4 runs on
   Turing. That would still need the harness's own GPU assertion patched and a GGUF code-model, and it
   is unverified. It remains the only road left, and it is a real project with a real chance of failing.
4. **`mbmmurad`'s "LB 0.86 (3rd place candidate)" is worth a look** if we ever get hardware: it is the
   only non-Qwen, non-Duck entry claiming a top placement, and it uses Gemma-4 31B. Note it has **0
   private datasets** and **0 public datasets** — so it may be a Milestone-1 score, and its title says
   "milestone" without saying which.
