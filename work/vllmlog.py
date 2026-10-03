import json, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
b = pathlib.Path("work/vllm_log.json").read_bytes()
t = None
for enc in ("utf-16","utf-16-le","utf-8"):
    try:
        x = b.decode(enc)
        if "PROBE" in x or "nvidia-smi" in x: t = x; break
    except Exception: pass
if t is None:
    print("decode failed, raw head:"); print(b[:600]); raise SystemExit
i = t.find("[")
try:
    j = json.loads(t[i:]); txt = "".join(e.get("data","") for e in j)
except Exception:
    txt = t
for line in txt.split("\n"):
    s = line.rstrip()
    if s.strip(): print("  | %s" % s[:190])
