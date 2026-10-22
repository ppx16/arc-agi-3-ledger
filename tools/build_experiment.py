"""Build an ARC experiment kernel that differs from the reference by exactly one environment value.

The research plan (F88/F89) needs a series of one-change-at-a-time variants of a 569 KB notebook. Doing that
by hand is how a "one-line change" quietly becomes three. So this copies the reference notebook, substitutes a
single line inside the `setup_env` dictionary, and refuses unless exactly one cell changed and only that line
changed within it.

Usage:
    python work/build_experiment.py <name> <ENV_KEY> <new literal> [--dry-run]
e.g.
    python work/build_experiment.py streams25 ARC3_MAX_ACTIVE_STREAMS 25
    python work/build_experiment.py nothink  LOCAL_ANALYZER_ENABLE_THINKING "'false'"
"""
import hashlib
import json
import re
import sys
from pathlib import Path

REF = Path(r'D:\kaggle\arc\scratch\inspect')
OUTROOT = Path(r'D:\kaggle\arc\kernels')
REF_ID = 'ppxl16/arc-agi-3-m2-franzen-verbatim'


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        raise SystemExit(__doc__)
    name, key, literal = argv[1], argv[2], argv[3]
    dry = '--dry-run' in argv

    nb_path = next(REF.glob('*.ipynb'))
    meta0 = json.loads((REF / 'kernel-metadata.json').read_text(encoding='utf-8'))
    raw = nb_path.read_bytes().decode('utf-8-sig')
    nb0 = json.loads(raw)
    if meta0.get('id') != REF_ID:
        raise SystemExit('REFUSING: the reference is %r, expected %r' % (meta0.get('id'), REF_ID))

    pat = re.compile(r"(?m)^(\s*)'%s':\s*[^,\n]+,(\s*(?:#.*)?)$" % re.escape(key))
    hits = [(i, c) for i, c in enumerate(nb0['cells'])
            if pat.search(c['source'] if isinstance(c['source'], str) else ''.join(c['source']))]
    if len(hits) != 1:
        raise SystemExit('REFUSING: %s appears as an assignment in %d cells, expected 1'
                         % (key, len(hits)))
    ci = hits[0][0]
    cell = hits[0][1]
    text = cell['source'] if isinstance(cell['source'], str) else ''.join(cell['source'])
    new_text, n = pat.subn(lambda m: "%s'%s': %s,%s" % (m.group(1), key, literal, m.group(2)), text, count=1)
    if n != 1 or new_text == text:
        raise SystemExit('REFUSING: the substitution did not apply exactly once')

    nb = json.loads(raw)
    tgt = nb['cells'][ci]
    tgt['source'] = new_text if isinstance(tgt['source'], str) else new_text.splitlines(keepends=True)
    changed = [i for i, (a, b) in enumerate(zip(nb0['cells'], nb['cells']))
               if (a['source'] if isinstance(a['source'], str) else ''.join(a['source']))
               != (b['source'] if isinstance(b['source'], str) else ''.join(b['source']))]
    if changed != [ci]:
        raise SystemExit('REFUSING: cells changed = %s, expected only [%d]' % (changed, ci))

    # Validate the substituted ENTRY, not the whole cell: cell 4 contains IPython magics (!pip, %env), so
    # compiling it wholesale fails for reasons that have nothing to do with this edit. The entry is checked
    # as a dict literal, which is exactly the syntax context it lives in.
    entry = pat.search(new_text).group(0).strip().rstrip(',')
    try:
        import ast
        parsed = ast.parse('{%s}' % entry, mode='eval')
        if not isinstance(parsed.body, ast.Dict) or len(parsed.body.keys) != 1:
            raise SyntaxError('not a single dict entry')
    except SyntaxError as exc:
        raise SystemExit('REFUSING: the substituted entry does not parse as a dict item (%s): %r'
                         % (exc, entry))

    print('cell %d: substituted %s -> %s' % (ci, key, literal))
    print('  before: %s' % pat.search(text).group(0).strip()[:90])
    print('  after : %s' % pat.search(new_text).group(0).strip()[:90])
    if dry:
        print('DRY RUN: nothing written')
        return 0

    slug = 'arc-exp-%s' % name
    title = 'ARC exp %s' % name
    if re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', title.lower())).strip('-') != slug:
        raise SystemExit('REFUSING: title does not slugify to the id (%r vs %r)' % (title, slug))
    meta = json.loads(json.dumps(meta0))
    meta.pop('id_no', None)
    meta['id'] = 'ppxl16/' + slug
    meta['title'] = title
    meta['code_file'] = slug + '.ipynb'
    meta['is_private'] = True
    for k, v in meta0.items():
        if k in ('id', 'title', 'code_file', 'is_private', 'id_no'):
            continue
        if json.dumps(meta.get(k), sort_keys=True) != json.dumps(v, sort_keys=True):
            raise SystemExit('REFUSING: environment field %s changed' % k)

    out = json.dumps(nb, ensure_ascii=True)
    if json.loads(out) != nb or not out.isascii():
        raise SystemExit('REFUSING: ASCII round-trip failed')
    dst = OUTROOT / ('kernel-' + slug)
    dst.mkdir(parents=True, exist_ok=True)
    (dst / meta['code_file']).write_text(out, encoding='utf-8')
    (dst / 'kernel-metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print('built %s  (%d B, sha %s)' % (dst, len(out), hashlib.sha256(out.encode()).hexdigest()[:16]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
