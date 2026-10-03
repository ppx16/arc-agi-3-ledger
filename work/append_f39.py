"""Append work/F39_note.md to the end of the F39 section in FINDINGS.md (CRLF preserved)."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
note = (ROOT / "work" / "F39_note.md").read_text(encoding="utf-8")
note = note.replace("\r\n", "\n").replace("\n", "\r\n").rstrip("\r\n") + "\r\n"
p = ROOT / "FINDINGS.md"
old = p.read_text(encoding="utf-8", newline="")
i = old.find("## F39. ")
if i < 0:
    sys.exit("!! F39 section not found")
new = old[:i].rstrip("\r\n") + "\r\n\r\n---\r\n" + \
      old[i:].replace("\r\n", "\n").replace("\n", "\r\n").rstrip("\r\n") + "\r\n" + note
p.write_text(new, encoding="utf-8", newline="")
d = p.read_bytes()
print("bytes", len(d), "crlf", d.count(b"\r\n"), "loneLF", d.count(b"\n") - d.count(b"\r\n"))
print("F39 sections:", new.count("## F39."), "note appended:", "39.1 State at" in new)
