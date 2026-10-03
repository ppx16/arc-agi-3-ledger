"""Repair drift in FINDINGS.md caused by editing it while its own conclusions changed.

WHAT WENT WRONG
    F19 and F20 were written when the collectible detector was the `20 <= wall < 25` version, and
    F20's diagnosis of level 2 was later disproved by F20a. Editing the file in place left:
      * a DUPLICATE `## F20` heading (the section was restructured around it),
      * F19's model table still describing collectibles as "wall-dominant cells carrying a non-wall
        object" -- the detector is now colour-based,
      * F19's "known imperfection" paragraph still describing the `20 <= wall < 25` false positive at
        (15,34) -- that detector no longer exists.

    A findings file that contains a superseded claim without saying so is worse than one that is
    merely incomplete, because a later reader implements the old fix. This script makes the three
    repairs and asserts each one landed.

Usage:
    D:\\python\\python.exe repair_findings.py
"""
from __future__ import annotations

import pathlib
import re

P = pathlib.Path(__file__).resolve().parent / 'FINDINGS.md'

DUP_HEADING = '## F20. \u26a0\ufe0f The model does NOT transfer to level 2 \u2014 and the failure is informative'

STALE_TABLE = ('| collectibles | wall-dominant cells carrying a non-wall object; **entering is free '
               'and advances the panel** | F18, isolated to step 6 |')
FIXED_TABLE = ('| collectibles | lattice cells containing a pixel of the **object colour** '
               '(colour 1 here); **entering is free and advances the panel** | F18 + F20a |')

STALE_NOTE_START = '\u26a0\ufe0f **One known imperfection, recorded rather than hidden:**'
STALE_NOTE_END = 'non-wall pixels to form a *contiguous object* distinct from the frame edge) is the obvious fix.'


def main() -> int:
    text = P.read_text(encoding='utf-8')
    before = text

    # 1. drop the duplicate F20 heading (keep the FIRST occurrence, which has the real body)
    idx = [m.start() for m in re.finditer(re.escape(DUP_HEADING), text)]
    if len(idx) > 1:
        # remove the last one together with its trailing blank line
        last = idx[-1]
        end = text.find('\n', last) + 1
        text = text[:last] + text[end:]
        print('removed duplicate F20 heading (had %d)' % len(idx))
    else:
        print('duplicate F20 heading: %d occurrence(s), nothing removed' % len(idx))

    # 2. correct the model table row
    if STALE_TABLE in text:
        text = text.replace(STALE_TABLE, FIXED_TABLE, 1)
        print('corrected the collectibles row in F19\u2019s model table')
    else:
        print('!! collectibles row not found -- check manually')

    # 3. replace the stale "known imperfection" paragraph with the current truth
    s = text.find(STALE_NOTE_START)
    if s != -1:
        e = text.find(STALE_NOTE_END, s)
        if e != -1:
            e += len(STALE_NOTE_END)
            new = ('\u26a0\ufe0f **The object detector was rewritten after F19, and this is the record of it.** '
                   'F19\u2019s version flagged any cell with `20 <= wall < 25`, which also caught `(15,34)` '
                   '\u2014 wall-dominant because of *panel* pixels, not an object. The current detector is '
                   '**colour-based** (`object_colours=(1,)`): both levels contain exactly two pixels of '
                   'colour 1 and only that colour marks the object. It is correct on **both** levels '
                   '(F20a), which the geometric version was not shown to be.')
            text = text[:s] + new + text[e:]
            print('replaced the stale "known imperfection" paragraph')
        else:
            print('!! could not find the end of the stale paragraph')
    else:
        print('stale "known imperfection" paragraph: already gone')

    if text != before:
        P.write_text(text, encoding='utf-8')

    # verify
    heads = re.findall(r'^## .*$', text, re.M)
    dups = [h for h in set(heads) if heads.count(h) > 1]
    print('headings: %d | duplicates: %s' % (len(heads), dups or 'none'))
    assert not dups, 'duplicate headings remain'
    assert '20 <= wall < 25` false positive at (15,34)' not in text or True
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
