"""Minimal probe: can vLLM actually serve on Kaggle's 2x Tesla T4 (cc 7.5)?

WHY THIS RUN EXISTS
    F43 established, by measurement, that `machine_shape: NvidiaRtxPro6000` is accepted and then
    SILENTLY IGNORED -- our account gets 2x Tesla T4, cc 7.5, 14.6 GB each. That kills the public
    Duck recipe as published:
      * `foysalemonshanto/qwen3-8-27b-fp8-repacked-v1` is FP8, and FP8 needs cc >= 8.9;
      * `driessmit1/arc3-vllm-h100-wheelhouse-v3` is compiled for H100 (sm_90).
    BUT F42.4's actual claim is that what we lack is "a model that reads a structured board
    description and writes code" -- not specifically a 27B model. The Duck harness is
    model-agnostic (`analyzer_model` is an env var). So the tractable question is whether ANY
    code-capable model can be SERVED on this hardware.

    This probe answers exactly that and nothing else. It is the one step that can veto the whole
    plan, so it runs FIRST rather than after a notebook is built around it.

WHAT IT DECIDES
    PASS  -> vLLM serves on cc 7.5 at float16. The remaining work is engineering (pick a
             quantisation that fits, wire the harness), not feasibility.
    FAIL  -> record which stage failed; PyPI vLLM's Turing support is the first suspect, the
             H100 wheelhouse the second. Then the plan needs a different serving stack
             (llama.cpp is plausible: the TAAF bundle ships configs/inference.local.llama.json).

⚠️ Deliberately NOT attempted here
    * the 27B model -- this probe is about the SERVING STACK, not the model. A small model proves
      the plumbing far faster and cannot be blamed for a vLLM/Turing failure.
    * `pip install vllm` is large and slow, so it is time-boxed and its failure is reported
      distinctly from a runtime failure.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time

T0 = time.time()
MODEL = os.environ.get("PROBE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")


def stamp(msg: str) -> None:
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def run(cmd: list[str], timeout: int = 1800) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after %ds" % timeout
    except Exception as e:  # noqa: BLE001
        return 1, repr(e)


stamp("=== VLLM-ON-T4 PROBE ===")
stamp("python %s | machine %s" % (sys.version.split()[0], platform.machine()))

rc, out = run(["nvidia-smi", "--query-gpu=name,memory.total,compute_cap", "--format=csv"])
stamp("nvidia-smi rc=%s -> %s" % (rc, out.strip().replace("\n", " ; ")[:300]))

try:
    import torch
    for i in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(i)
        stamp("  dev%d %s %.1fGB cc=%d.%d bf16_supported=%s"
              % (i, p.name, p.total_memory / 2 ** 30, p.major, p.minor,
                 torch.cuda.is_bf16_supported()))
except Exception as e:  # noqa: BLE001
    stamp("torch probe failed: %r" % (e,))

# ---------------------------------------------------------------- 1. install
stamp("--- 1. pip install vllm (time-boxed 1500s) ---")
rc, out = run([sys.executable, "-m", "pip", "install", "-q", "--no-input", "vllm"], timeout=1500)
stamp("pip rc=%s" % rc)
tail = out.strip().splitlines()[-12:]
for ln in tail:
    stamp("    | %s" % ln[:150])
if rc != 0:
    stamp("VERDICT: FAIL at INSTALL -- vLLM could not be installed. (not a hardware verdict)")
    raise SystemExit(0)

# ---------------------------------------------------------------- 2. import
stamp("--- 2. import vllm ---")
try:
    import vllm
    stamp("vllm version: %s" % getattr(vllm, "__version__", "?"))
    ok = True
except Exception as e:  # noqa: BLE001
    import traceback
    stamp("import FAILED: %r" % (e,))
    stamp(traceback.format_exc()[-1500:])
    ok = False
if not ok:
    stamp("VERDICT: FAIL at IMPORT -- PyPI vLLM cannot load on cc 7.5.")
    raise SystemExit(0)

# ---------------------------------------------------------------- 3. serve
stamp("--- 3. load %s in float16 and generate ---" % MODEL)
try:
    from vllm import LLM, SamplingParams
    t = time.time()
    llm = LLM(model=MODEL, dtype="float16", trust_remote_code=True,
              gpu_memory_utilization=0.85, max_model_len=2048,
              enforce_eager=True, tensor_parallel_size=1)
    stamp("LLM() constructed in %.1fs" % (time.time() - t))
    t = time.time()
    outs = llm.generate(["def fib(n):"],
                        SamplingParams(temperature=0.0, max_tokens=48))
    dt = time.time() - t
    text = outs[0].outputs[0].text if outs and outs[0].outputs else ""
    stamp("generate() ok in %.1fs" % dt)
    stamp("SAMPLE OUTPUT >>> %s" % text.strip().replace("\n", " / ")[:300])
    stamp("VERDICT: *** PASS *** -- vLLM serves on 2x T4 at float16.")
except Exception as e:  # noqa: BLE001
    import traceback
    stamp("serve FAILED: %r" % (e,))
    stamp(traceback.format_exc()[-2500:])
    stamp("VERDICT: FAIL at SERVE -- vLLM imported but cannot run on cc 7.5.")

stamp("=== END (total %.1fs) ===" % (time.time() - T0))
