import platform
import subprocess
import sys

print("=== GPU PROBE ===")
print("machine:", platform.machine(), "| python:", sys.version.split()[0])

try:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,compute_cap", "--format=csv"],
        capture_output=True, text=True, timeout=60)
    print("nvidia-smi rc=%s" % out.returncode)
    print(out.stdout.strip()[:600])
    if out.stderr:
        print("stderr:", out.stderr.strip()[:300])
except Exception as e:
    print("nvidia-smi failed:", repr(e)[:200])

try:
    import torch
    print("torch:", torch.__version__, "cuda avail:", torch.cuda.is_available())
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            print("  dev%d %s  %.1f GB  cc=%d.%d"
                  % (i, p.name, p.total_memory / 2 ** 30, p.major, p.minor))
except Exception as e:
    print("torch probe failed:", repr(e)[:200])

print("=== END ===")
