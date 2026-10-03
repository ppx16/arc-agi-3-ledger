"""Probe v3: mount the public ARC vLLM wheelhouses and see if ANY of them imports on 2x T4.

WHERE WE ARE
    * `machine_shape` is silently ignored -- we get 2x Tesla T4, cc 7.5 (measured).
    * The TAAF bundle's own setup asserts the GPU is `rtx-pro-6000` / `h100` / `l4`, and pins
      `flashinfer==0.6.6` (sm_80+). Both exclude Turing by construction.
    * Stock PyPI vLLM **cannot even import**: `vllm._C_stable_libtorch` links
      `libcudart.so.13` while the image ships CUDA 12.8 (`libcudart.so.12` only). Measured twice.
    * But CUDA **12.9** and 12.8 share the `libcudart.so.12` SONAME, and the community publishes
      ARC-specific wheelhouses -- notably `saltb0x/arc3-vllm-wheelhouse-v0271-cu129` (vLLM 0.27.1,
      cu129). So there is a real chance a prebuilt ARC wheel imports where the stock one does not.

WHAT THIS PROBE DECIDES
    PASS -> a prebuilt ARC wheelhouse works on cc 7.5. The route reopens and the remaining
            questions are model size and speed, which are trade-offs rather than blockers.
    FAIL -> five independent gates all point the same way; "serve an LLM on Kaggle T4" is closed
            and the Duck line needs hardware we cannot obtain.

⚠️ The first risk to check is the WHEEL TAG: the image runs Python 3.13 (cp313), and several of
these wheelhouses are tagged cp312. A tag mismatch is not a hardware verdict, so it is reported
distinctly rather than being mistaken for one.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import time

T0 = time.time()
WHEELHOUSES = [
    "saltb0x/arc3-vllm-wheelhouse-v0271-cu129",
    "dominic789654/arc-vllm026",
    "mirzamilanfarabi/arc3-vllm-h100-wheelhouse-v3",
]
SMALL = "Qwen/Qwen2.5-0.5B-Instruct"


def stamp(m: str) -> None:
    print("[%7.1fs] %s" % (time.time() - T0, m), flush=True)


def run(cmd, timeout=1800):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT %ds" % timeout
    except Exception as ex:  # noqa: BLE001
        return 1, repr(ex)


stamp("=== ARC-vLLM WHEELHOUSE PROBE v3 ===")
stamp("python %s" % sys.version.replace("\n", " ")[:90])
rc, out = run(["nvidia-smi", "--query-gpu=name,compute_cap", "--format=csv,noheader"])
stamp("gpu: %s" % out.strip().replace("\n", " ; ")[:160])

roots = glob.glob("/kaggle/input/**/", recursive=True)
for ref in WHEELHOUSES:
    slug = ref.split("/")[-1]
    cands = [d for d in roots if slug in d] or glob.glob("/kaggle/input/**/%s*" % slug, recursive=True)
    cands = sorted(set(cands))
    stamp("--- %s -> %s" % (ref, cands[:2] if cands else "NOT MOUNTED"))
    for root in cands[:1]:
        whl = glob.glob(os.path.join(root, "**", "*.whl"), recursive=True)
        stamp("    %d wheels; tags: %s" % (len(whl), sorted({os.path.basename(w).split("-")[-1] for w in whl})[:6]))
        for w in whl:
            b = os.path.basename(w)
            if b.startswith("vllm-") or "torch" in b:
                stamp("      %s" % b[:120])

# try each wheelhouse in turn until vllm imports
imported = False
for ref in WHEELHOUSES:
    slug = ref.split("/")[-1]
    cands = sorted({d for d in roots if slug in d})
    if not cands:
        continue
    whl_dir = cands[0]
    stamp("--- pip install from %s (no index) ---" % slug)
    rc, out = run([sys.executable, "-m", "pip", "install", "-q", "--no-input",
                   "--no-index", "--find-links", whl_dir, "vllm"], timeout=1500)
    stamp("    pip rc=%s" % rc)
    for l in out.strip().splitlines()[-5:]:
        stamp("      | %s" % l[:150])
    try:
        import importlib
        import vllm  # noqa: F401
        importlib.reload(vllm)
        stamp("    vllm %s IMPORTED" % getattr(vllm, "__version__", "?"))
        imported = True
        break
    except Exception as e:  # noqa: BLE001
        stamp("    import failed: %r" % (str(e)[:200],))

if not imported:
    stamp("VERDICT: FAIL -- none of the mounted ARC wheelhouses yields an importable vllm on this image.")
    stamp("=== END (%.1fs) ===" % (time.time() - T0))
    raise SystemExit(0)

stamp("--- serve %s fp16, enforce_eager, no flashinfer ---" % SMALL)
os.environ["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
os.environ["VLLM_ATTENTION_BACKEND"] = "XFORMERS"
try:
    from vllm import LLM, SamplingParams
    t = time.time()
    llm = LLM(model=SMALL, dtype="float16", trust_remote_code=True,
              gpu_memory_utilization=0.80, max_model_len=1024,
              enforce_eager=True, tensor_parallel_size=1)
    stamp("LLM() ok in %.1fs" % (time.time() - t))
    t = time.time()
    o = llm.generate(["def fib(n):"], SamplingParams(temperature=0.0, max_tokens=32))
    stamp("generate ok in %.1fs" % (time.time() - t))
    stamp("SAMPLE >>> %s" % (o[0].outputs[0].text if o and o[0].outputs else "").strip()[:200])
    stamp("VERDICT: *** PASS *** -- a prebuilt ARC wheelhouse serves on cc 7.5.")
except Exception as e:  # noqa: BLE001
    import traceback
    stamp("serve FAILED: %r" % (e,))
    stamp(traceback.format_exc()[-1800:])
    stamp("VERDICT: FAIL at SERVE -- wheelhouse imports but cannot run on cc 7.5.")
stamp("=== END (%.1fs) ===" % (time.time() - T0))
