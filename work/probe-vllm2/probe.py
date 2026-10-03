"""Probe v2: can ANY vLLM serve on cc 7.5 here, once the CUDA version is matched?

WHAT PROBE v1 SETTLED, AND WHAT IT DID NOT
    v1 failed at `import vllm` with `ImportError: libcudart.so.13: cannot open shared object file`.
    That is a **CUDA runtime version mismatch**, not an architecture verdict: the PyPI wheel now
    targets CUDA 13 while the Kaggle image is torch 2.11.0+cu128. So v1 said nothing about Turing.

    Since then, reading the TAAF bundle's own `setup_commands.json` showed the published Duck stack
    is gated on hardware three separate ways:
      * an explicit `assert` on the GPU name (`rtx-pro-6000` / `h100` / `l4` -- T4 fails it);
      * `flashinfer==0.6.6`, which needs sm_80+ (Ampere) and does not list Turing;
      * the model is FP8, which needs cc >= 8.9.
    So the published stack is Hopper/Blackwell-only **by construction**, not merely by model size.

    The remaining open question -- and the only one worth another GPU run -- is whether a
    **different** serving stack works on this hardware at all:
        vLLM built against cu128  +  an fp16 model  +  enforce_eager (no flashinfer, no FA2)
    If yes, a 4-bit quantisation across the two T4s is at least conceivable. If no, the route is
    closed on our hardware and no amount of model-shopping changes that.

WHAT IT DECIDES
    PASS -> vLLM can serve on cc 7.5 with the CUDA-matched wheel; the constraint becomes model size
            and speed, which are engineering trade-offs.
    FAIL -> record the stage. Combined with the three gates above, that closes "serve an LLM on
            Kaggle T4" and the Duck route needs rented hardware or a different competition surface.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

T0 = time.time()
SMALL = "Qwen/Qwen2.5-0.5B-Instruct"


def stamp(m: str) -> None:
    print("[%7.1fs] %s" % (time.time() - T0, m), flush=True)


def run(cmd: list[str], timeout: int = 1800, env: dict | None = None):
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=e)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT %ds" % timeout
    except Exception as ex:  # noqa: BLE001
        return 1, repr(ex)


stamp("=== VLLM-ON-T4 PROBE v2 ===")
rc, out = run(["nvidia-smi", "--query-gpu=name,memory.total,compute_cap", "--format=csv"])
stamp("gpu: %s" % out.strip().replace("\n", " ; ")[:220])
try:
    import torch
    stamp("torch %s cuda %s" % (torch.__version__, torch.version.cuda))
    for i in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(i)
        stamp("  dev%d %s %.1fGB cc=%d.%d" % (i, p.name, p.total_memory / 2 ** 30, p.major, p.minor))
    stamp("libcudart present: %s" % sorted(
        os.path.basename(x) for x in __import__("glob").glob("/usr/local/cuda*/lib64/libcudart.so*")
    )[:6])
except Exception as e:  # noqa: BLE001
    stamp("torch probe: %r" % (e,))

stamp("--- available vllm versions (last 12) ---")
rc, out = run([sys.executable, "-m", "pip", "index", "versions", "vllm"], timeout=240)
lines = [l.strip() for l in out.splitlines() if "Available versions" in l or l.strip().startswith("vllm")]
for l in lines[:3]:
    stamp("   %s" % l[:400])

# torch is 2.11.0+cu128 on this image; ask vLLM for a build that matches instead of letting pip
# drag in a CUDA-13 runtime.
ATTEMPTS = [
    ("cu128 extra-index, no torch upgrade",
     [sys.executable, "-m", "pip", "install", "-q", "--no-input",
      "--extra-index-url", "https://download.pytorch.org/whl/cu128",
      "vllm", "--no-build-isolation"]),
    ("pin torch back to the image's 2.11.0+cu128 after install",
     [sys.executable, "-m", "pip", "install", "-q", "--no-input",
      "torch==2.11.0", "--index-url", "https://download.pytorch.org/whl/cu128"]),
]

for label, cmd in ATTEMPTS:
    stamp("--- install: %s ---" % label)
    rc, out = run(cmd, timeout=1500)
    stamp("rc=%s" % rc)
    for l in out.strip().splitlines()[-6:]:
        stamp("    | %s" % l[:150])

stamp("--- import vllm ---")
try:
    import vllm
    stamp("vllm %s IMPORTED" % getattr(vllm, "__version__", "?"))
    imported = True
except Exception as e:  # noqa: BLE001
    import traceback
    stamp("import FAILED: %r" % (e,))
    stamp(traceback.format_exc()[-1200:])
    imported = False

if imported:
    stamp("--- serve %s fp16, enforce_eager ---" % SMALL)
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    os.environ.setdefault("VLLM_ATTENTION_BACKEND", "XFORMERS")
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
        stamp("VERDICT: *** PASS *** -- vLLM serves on cc 7.5 with a CUDA-matched build.")
    except Exception as e:  # noqa: BLE001
        import traceback
        stamp("serve FAILED: %r" % (e,))
        stamp(traceback.format_exc()[-2000:])
        stamp("VERDICT: FAIL at SERVE on cc 7.5.")
else:
    stamp("VERDICT: FAIL at IMPORT even after CUDA matching.")

stamp("=== END (%.1fs) ===" % (time.time() - T0))
