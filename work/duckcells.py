import json, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
nb = json.loads(next(pathlib.Path("work/duck9").glob("*.ipynb")).read_text(encoding="utf-8", errors="replace"))
for i in (3, 8, 9):
    print("="*100)
    print("CELL %d" % i)
    print("="*100)
    print("".join(nb["cells"][i].get("source", []))[:3000])
