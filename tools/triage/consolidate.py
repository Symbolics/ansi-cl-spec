"""Consolidate triage outputs and dry-run all proposed fixes on a copy.

Usage: python3 consolidate.py <repo> <triage_out_dir> <result_dir>
Writes <result_dir>/fixes.json (flat list of {file, old, new, secno, item, summary, confidence, group}),
<result_dir>/counts.json, and reports problems: old not found, not unique, overlapping fixes,
XHTML not well-formed after applying.
"""
import json, sys, collections, shutil
from pathlib import Path
from lxml import etree

repo, tdir, rdir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
rdir.mkdir(parents=True, exist_ok=True)
records, fixes = [], []
for f in sorted(tdir.glob('*.json')):
    g = f.stem
    for r in json.loads(f.read_text()):
        r['group'] = g
        records.append(r)
        fl = []
        if isinstance(r.get('fix'), dict):
            fl.append(r['fix'])
        elif isinstance(r.get('fix'), list):
            fl += r['fix']
        if isinstance(r.get('fixes'), list):
            fl += [x for x in r['fixes'] if x not in fl]
        for x in fl:
            if x and x.get('old') and x.get('new') is not None:
                fixes.append(dict(file=r['file'], old=x['old'], new=x['new'], secno=r.get('secno'),
                                  item=r.get('item'), summary=r.get('summary'),
                                  confidence=r.get('confidence'), group=g))
# dedupe identical fixes
seen, uniq = set(), []
for x in fixes:
    k = (x['file'], x['old'], x['new'])
    if k not in seen:
        seen.add(k); uniq.append(x)
fixes = uniq

counts = collections.Counter((r['group'], r['category']) for r in records)
cat = collections.Counter(r['category'] for r in records)
problems = []
byfile = collections.defaultdict(list)
for x in fixes:
    p = x['file'] if x['file'].startswith('OEBPS/') else 'OEBPS/' + x['file']
    x['file'] = p
    byfile[p].append(x)
for p, fl in byfile.items():
    path = repo / 'src' / p
    s = path.read_text(encoding='utf-8')
    spans = []
    for x in fl:
        n = s.count(x['old'])
        if n != 1:
            problems.append(f"{p} [{x['secno']}]: old occurs {n} times: {x['old'][:80]!r}")
            continue
        i = s.index(x['old']); spans.append((i, i + len(x['old']), x))
    spans.sort(key=lambda t: t[0])
    for a, b in zip(spans, spans[1:]):
        if a[1] > b[0]:
            problems.append(f"{p}: overlapping fixes at {a[0]} and {b[0]}")
    t = s
    for i, j, x in sorted(spans, key=lambda t: -t[0]):
        t = t[:i] + x['new'] + t[j:]
    try:
        etree.fromstring(t.encode('utf-8'), etree.XMLParser(resolve_entities=False))
    except etree.XMLSyntaxError as e:
        problems.append(f"{p}: not well-formed after fixes: {e}")

(rdir / 'fixes.json').write_text(json.dumps(fixes, indent=1, ensure_ascii=False))
(rdir / 'counts.json').write_text(json.dumps({'by_category': cat, 'by_group_category': {f'{g}:{c}': n for (g, c), n in counts.items()}}, indent=1))
print('records', len(records), dict(cat))
print('fixes', len(fixes), 'files', len(byfile), 'by group', dict(collections.Counter(x['group'] for x in fixes)))
print('problems', len(problems))
for pr in problems:
    print('  ', pr)
