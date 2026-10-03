# F44. ⛔ "Serve an LLM on Kaggle T4" is CLOSED — six independent gates, all measured

> ## ⚠️ 更正 2026-10-03：闸门 1 是错的，而它正是承重的那一道
>
> 见 **[F46](F46-accelerator-push-path.md)**。
>
> 下文中**关于 T4 的一切都是实测的、准确的**。错的是从闸门 1 推出的那个结论 ——
> **"我们的账号只被授予 2×T4"**。
>
> 正确的读法：**CLI push 这条路径**会静默替换成默认卡，所以 `machine_shape`
> **根本无法表达**"我要 RTX Pro 6000"这个请求。那张卡是通过 **notebook 编辑器 UI** 分配的。
>
> 闸门 2–6 是真的，但它们**只在 T4 上成立**，换到 sm_120 的卡上会全部消失。
> 原文保留不改，作为记录。

Written 2026-10-04. Three GPU probe kernels were pushed, run, read and deleted to settle this
(`work/probe-gpu/`, `work/probe-vllm/`, `work/probe-vllm2/`, `work/probe-vllm3/`). Each probe was
built to answer one question and to be able to veto the whole line, so the answer arrived **before**
any notebook was built around it.

## The question
F42.4: our 0.18 equals the official CNN baseline, four different mechanisms all capped there, and the
top teams are 55–150× higher because they run **"The Duck"** — an LLM writing Python against a
structured board view, served by a local vLLM. The public stack is fully identified (F43). **Can we
serve a code-capable model at all on the hardware we are actually entitled to?**

## The answer: no — and every gate below is measured, not assumed

| # | gate | how it was established |
|---|---|---|
| 1 | **`machine_shape` is silently IGNORED** | probe requested `NvidiaRtxPro6000`; the push succeeded, the run COMPLETED, and it was handed **2× Tesla T4, 15360 MiB, cc 7.5**. ⚠️ Same failure class this repo keeps paying for: a field accepted and discarded, with **no error**. |
| 2 | **The recipe asserts the GPU by name** | its own `setup_commands.json`: `expected_gpu_type = os.getenv('KAGGLE_GPU_TYPE','rtx-pro-6000')`, `patterns {'rtx-pro-6000','h100','l4'}`, then `assert not mismatched`. **A T4 fails that assert immediately.** |
| 3 | **`flashinfer==0.6.6`** | pinned in the same file (`STAMP_TEXT = 'vllm==0.19.0 torch==2.10.0 flashinfer==0.6.6'`). FlashInfer requires **sm_80+ (Ampere)**; Turing is absent. |
| 4 | **The model is FP8** | `vrfai/Qwen3.6-27B-FP8` (that bundle) and `Qwen/Qwen3.8-27B-FP8` (the LB-9 bundle). FP8 needs **cc ≥ 8.9**; T4 is 7.5. |
| 5 | **Stock PyPI vLLM cannot even import** | `pip install vllm` rc=0, then `ImportError: libcudart.so.13: cannot open shared object file`. The image is torch 2.11.0+**cu128** and ships only `libcudart.so.12`. `vllm._C_stable_libtorch` is a **prebuilt binary linked against CUDA 13** — pinning torch back does not help. Reproduced twice. |
| 6 | **The community ARC wheelhouses do not install** | mounted three (`saltb0x/arc3-vllm-wheelhouse-v0271-cu129`, `dominic789654/arc-vllm026`, `mirzamilanfarabi/arc3-vllm-h100-wheelhouse-v3`). All three mount and their `vllm` wheels are `cp38-abi3` (stable ABI — so the **tag is not the problem**, they would work on this Python 3.13). `pip install --no-index --find-links <dir> vllm` returned **rc=1 for all three**: offline dependency resolution fails. |

⇒ **Gates 1–4 alone are structural.** Gate 1 is a *hardware entitlement* limit: the teams at 20–28
run RTX Pro 6000 / H100, and no amount of engineering changes which GPU Kaggle hands us. Gates 5–6
were the last two things worth testing, and both failed.

## Why this is not "we gave up too early"
Each probe was the **cheapest** experiment that could falsify the plan, and each was run **before**
building anything on top of it — which is the opposite of the EffB0 sequence, where the rationale was
only re-tested after three 4-hour runs. Total cost here: **three short CPU/GPU script runs** (4.2, 9.9
and 4.9 minutes).

## What is NOT closed, and what it would take
* **The Duck recipe itself is fully identified and entirely public.** `docs/FINDINGS.md` F43 has the
  datasets, the model refs, the harness, the serving config and the gateway details. Nothing about it
  is secret or unknown.
* **A different serving stack on cc 7.5** — the only unexhausted variant is *not* using vLLM at all.
  ⚠️ `llama.cpp` is plausible: the TAAF bundle ships **`configs/inference.local.llama.json`**, which
  means the harness has a llama.cpp path, and GGUF Q4 runs on Turing. It would need a GGUF
  code-model (e.g. `ugvfpdcuwfnh/qwen3-8-27b-ud-q4-k-xl`) and the harness's assertion patched. **This
  was not tested** and it is the one remaining route; it is a real project with a real chance of
  failing on the harness's own assumptions.
* **Rented hardware cannot help.** The submission is a Kaggle notebook that Kaggle **reruns** on its
  own machines, so a rented GPU can develop but cannot submit. That is why `autodl` does not solve
  this one.

## The honest strategic read for ARC-AGI-3
Our 0.18 is a floor set by **absent hardware**, not only by absent method. The public recipe needs a
Hopper/Blackwell-class GPU and we are entitled to 2× T4. Any plan that assumes the published Duck
stack is therefore unreachable **as published**, and the realistic options are:

1. **Test the llama.cpp route on cc 7.5** (the only untested path; needs a GGUF code model, the
   harness's local-llama config, and the GPU assert patched);
2. **Accept 0.18** and stop spending on a line gated on hardware we cannot obtain;
3. Re-examine whether ARC-AGI-3 has a **non-LLM** score surface at all — every mechanism this repo
   built (novelty walk, portfolio, CNN baseline, learner-lifecycle change) tied the baseline exactly,
   which is evidence *against* that.
