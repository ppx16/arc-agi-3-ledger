import json, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = next(pathlib.Path("work/duck9").glob("*.ipynb"))
nb = json.loads(p.read_text(encoding="utf-8", errors="replace"))
print("cells:", len(nb["cells"]))
for i, c in enumerate(nb["cells"]):
    s = "".join(c.get("source", []))
    first = next((l for l in s.split("\n") if l.strip()), "")
    tag = "MD  " if c["cell_type"] == "markdown" else "code"
    print("[%2d] %s %5d | %s" % (i, tag, len(s), first[:104]))
