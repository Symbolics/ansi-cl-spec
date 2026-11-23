"""Build triage work packages from the two audits, grouped by chapter.

Usage: python3 triage_packages.py <repo> <outdir>
Each package lists, per entry (keyed by secno): its current file (new layout),
text sections with ratio < 1 (with word diffs), and example steps classed
mismatch/error plus unparsed items, annotated with the Examples-section ratio.
"""
import json, sys, collections
from pathlib import Path

repo, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
pmap = json.loads((repo / 'tools/data/path-map.json').read_text())
text = json.loads((repo / 'audit/text/findings.json').read_text())['entries']
ex = json.loads((repo / 'audit/examples/findings.json').read_text())

GROUPS = {'g1': ['3', '4'], 'g2': ['5'], 'g3': ['6', '7', '8', '9', '10', '11'],
          'g4': ['12', '13'], 'g5': ['14', '15', '16', '17', '18', '19'],
          'g6': ['20', '21', '22', '23', '24', '25']}
chap2g = {c: g for g, cs in GROUPS.items() for c in cs}

items = collections.defaultdict(dict)
for t in text:
    sec = [s for s in t['sections'] if s['ratio'] < 1.0]
    exr = next((s['ratio'] for s in t['sections'] if s['label'] == 'Examples'), None)
    e = items[t['secno']]
    e.update(secno=t['secno'], names=t['names'], kind=t['kind'],
             file='OEBPS/' + pmap['text/' + t['epub_file']],
             tex_file=t['tex_file'], examples_ratio=exr, text_sections=sec,
             label_diff=t.get('label_diff'))
for x in ex:
    steps = [s for s in x['steps'] if s['class'] in ('mismatch', 'error')]
    if steps or x.get('unparsed') or x.get('skipped_reasons'):
        e = items[x['secno']]
        e['example_steps'] = steps
        e['example_unparsed'] = x.get('unparsed', [])
        e['example_skipped'] = x.get('skipped_reasons', [])

counts = {}
for g in GROUPS:
    pkg = [v for k, v in items.items()
           if chap2g.get(k.split('.')[0]) == g
           and (v.get('text_sections') or v.get('example_steps') or v.get('example_unparsed'))]
    pkg.sort(key=lambda v: [int(p) for p in v['secno'].split('.')])
    (out / f'{g}.json').write_text(json.dumps(pkg, indent=1, ensure_ascii=False))
    counts[g] = dict(entries=len(pkg),
                     text_sections=sum(len(v.get('text_sections', [])) for v in pkg),
                     example_steps=sum(len(v.get('example_steps', [])) for v in pkg),
                     unparsed=sum(len(v.get('example_unparsed', [])) for v in pkg),
                     ex_steps_where_examples_text_differs=sum(
                         len(v.get('example_steps', [])) for v in pkg
                         if v.get('examples_ratio') not in (None, 1.0)))
print(json.dumps(counts, indent=1))
