#!/usr/bin/env python3
"""F7 sweep: blueprint `\\uses` ingredients vs the Lean import closure, per `\\leanok` node.

For every blueprint node carrying `\\lean{decl}\\leanok`, list the nodes its statement and proof
`\\uses`, locate the Lean file that declares `decl`, and report which used nodes' declarations
are NOT in the transitive import closure of that file. Such an edge means the Lean proof took a
route the blueprint proof does not cite — which is either one of the two deliberate patterns
(a *setting* citation; *specification instead of citation*) or the recorded `[A]`-parent /
`[T]`-refinement pattern, or a finding. Also reports used nodes that carry no `\\lean` tag at all.

Run from anywhere inside the article repo:  python f7sweep.py [--root <repo>]
The nodes and their proofs come from `linkage`'s own blueprint parser (`linkage.parse_latex`), so
the sweep reads the blueprint the way `linkage check` does: the environment from `\\begin` to
`\\end`, `\\lean` and `\\leanok` anywhere in it (a newline or a `%` comment between them is fine),
the proof the next `proof` environment past any comments. `linkage.toml` `[paths].lean` (the Lean
project dir) says where Lean is: every `*.lean` under it except `.lake/` and `Skeleton/` is scanned.
Needs `linkage` importable (`uv run` in article-kit, or an installed `linkage`); failing that it
looks for the article-kit checkout this script sits in.
"""
import argparse, glob, io, os, re, sys, tomllib
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--root', default=None)
args = ap.parse_args()

def find_root(start):
    p = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(p, 'linkage.toml')):
            return p
        q = os.path.dirname(p)
        if q == p:
            sys.exit('no linkage.toml found above ' + start)
        p = q

try:
    from linkage import config as linkage_config, parse_latex
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 4)))
    from linkage import config as linkage_config, parse_latex

ROOT = find_root(args.root or os.getcwd())
cfg = tomllib.loads(io.open(os.path.join(ROOT, 'linkage.toml'), encoding='utf-8').read())
paths = cfg.get('paths', {})
lean_dir = os.path.join(ROOT, paths.get('lean', 'Formalization'))

nodes = {}
for node in parse_latex.parse(linkage_config.load(Path(ROOT), validate=False)).nodes:
    if node.label:
        nodes[node.label] = {'lean': node.lean, 'leanok': node.leanok,
                             'uses': node.uses + node.proof_uses}

lean_files = [f for f in glob.glob(os.path.join(lean_dir, '**', '*.lean'), recursive=True)
              if '.lake' not in f.replace('\\', '/').split('/') and 'Skeleton' not in f.replace('\\', '/').split('/')]
decl_file, imports = {}, {}
for f in lean_files:
    txt = io.open(f, encoding='utf-8').read()
    rel = os.path.relpath(f, lean_dir).replace('\\', '/')
    mod = rel[:-5].replace('/', '.')
    imports[mod] = re.findall(r'^import\s+(\S+)', txt, re.M)
    ns = []
    for line in txt.splitlines():
        mm = re.match(r'\s*namespace\s+(\S+)', line)
        if mm:
            ns.append(mm.group(1)); continue
        mm = re.match(r'\s*end\s+(\S+)', line)
        if mm and ns and ns[-1] == mm.group(1):
            ns.pop(); continue
        dm = re.match(r"\s*(?:@\[[^\]]*\]\s*)?(?:noncomputable\s+)?(?:protected\s+)?(theorem|lemma|def|structure|abbrev|axiom|instance)\s+([A-Za-z_][\w\.'₀-₉]*)", line)
        if dm:
            name = dm.group(2)
            full = '.'.join(ns + [name]) if ns else name
            decl_file.setdefault(full, mod)
            decl_file.setdefault(name, mod)

def find_file(decl):
    if decl in decl_file:
        return decl_file[decl]
    for k, v in decl_file.items():
        if decl.endswith('.' + k) or k.endswith('.' + decl):
            return v
    return None

closure_cache = {}
def closure(mod):
    if mod in closure_cache:
        return closure_cache[mod]
    seen, stack = set(), [mod]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        stack.extend(imports.get(m, []))
    closure_cache[mod] = seen
    return seen

out, count = [], 0
for label, n in nodes.items():
    if not n['leanok'] or not n['lean']:
        continue
    count += 1
    files = [find_file(d) for d in n['lean']]
    if any(f is None for f in files):
        out.append(f'?? {label}: declaration(s) {n["lean"]} not located')
        continue
    cl = set().union(*(closure(f) for f in files)) | set(files)
    missing, not_lean = [], []
    for u in sorted(set(n['uses'])):
        un = nodes.get(u)
        if not un:
            continue
        if not un['lean']:
            not_lean.append(u); continue
        ufs = [find_file(d) for d in un['lean']]
        if all(uf is not None and uf not in cl for uf in ufs):
            missing.append(f'{u}→{ufs[0].split(".")[-1]}')
    flag = ''
    if missing:
        flag += ' | uses-not-imported: ' + ', '.join(missing)
    if not_lean:
        flag += ' | uses-[A]/untagged: ' + ', '.join(not_lean)
    out.append(f'{label} [{files[0].split(".")[-1]}]{flag}')

sys.stdout.reconfigure(encoding='utf-8')
print('\n'.join(out))
print(f'\n{count} leanok nodes')
