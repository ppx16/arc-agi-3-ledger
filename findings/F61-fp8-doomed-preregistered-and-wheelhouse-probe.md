# F61 — 2026-10-11 — The FP8 duck run is pre-registered as doomed; the decisive probe is the wheelhouse import

## 1. What we pushed, and why it should fail (prediction written BEFORE reading the result)

`ppxl16/arc-duck-taaf` (fork of `fabioolival/arc-agi-3-v21-taaf-27b`, the only reproducible
duck-harness) was pushed and is RUNNING.

**But our own ledger already measured the blocker** (F43.2, 2026-10-04): a probe kernel that
requested `machine_shape: NvidiaRtxPro6000` **pushed, ran and COMPLETED — and was given 2× Tesla T4
(cc 7.5)**. ⇒ **`machine_shape` is accepted and then silently ignored on this account.**

⇒ **PRE-REGISTERED PREDICTION (recorded before the log is read):**
1. the run is given T4s, not an RTX Pro 6000;
2. the FP8 model cannot serve — a 27B FP8 is ~27 GB against 14.6 GB per device, **and cc 7.5 does
   not support FP8 at all** (needs cc ≥ 8.9), and the wheelhouse is named `…h100-wheelhouse…`;
3. therefore the run ends ERROR, and the number of GPU-hours it burns is pure loss.

**Why push it anyway**: the downside is bounded (a GPU slot), the kernel was already built, and
"the strongest reproducible harness does not even start on our hardware" is itself the fact that
decides the ARC plan. It is recorded as a bet, not as a hope.

## 2. The decisive probe (this is the actual next step, per F43.4)

F43.4's risk **#1** is *"`driessmit1/arc3-vllm-h100-wheelhouse-v3` may not import on cc 7.5 at
all — that is the first thing to test, not the last."*

So: **`ppxl16/arc-vllm-probe` v1 pushed** (`kernels/kernel-arc-vllm-probe/`, a *script* kernel).
It prints the real GPU, inventories the wheelhouse, attempts an offline `pip install --no-index`
of `vllm`, then reports three imports (`torch` / `vllm` / `transformers`) and whether vLLM can see
the GPU. Its own pre-registered prediction:
* P1 the machine is 2× T4 (not Pro 6000);
* P2 the import more likely FAILS than succeeds;
* P3 if the import succeeds, the only remaining blocker is the quantisation ⇒ next is a
  **W4A16 (GPTQ/AutoRound) 27B with vLLM pinned to `float16`** (T4 has no bfloat16 — F43.4 #2),
  or a **Q4_K_XL GGUF through llama.cpp**, which the TAAF source supports via
  `configs/inference.local.llama.json`.

**⇒ The branch is pre-decided**: import OK → swap the model, keep the harness. Import FAILED →
the h100 wheelhouse is unusable and the serving route must change (llama.cpp / GGUF).

## 3. What this round actually cost and produced

* produced: a **falsifiable prediction** about the FP8 run, and a **cheap decisive probe**;
* cost: one kernel push each, no submission slot spent (`1/day`, still untouched today);
* the ARC public-surface finding from F60 stands: almost every reproducible ARC kernel attaches
  the same two `dfranzen` datasets, i.e. **they are variations of what we already run** — which is
  why the duck family (only reproducible via `fabioolival`) is the only real step change on offer.
