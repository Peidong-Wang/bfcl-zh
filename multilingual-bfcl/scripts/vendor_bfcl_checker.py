"""Vendor the supplied BFCL checker; change import paths only, never scoring logic."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT.parent/'berkeley-function-call-leaderboard/bfcl_eval'
dest = ROOT/'src/multilingual_bfcl/_vendor/bfcl'
paths = ['constants/enums.py','constants/type_mappings.py',
         'eval_checker/ast_eval/ast_checker.py',
         'eval_checker/ast_eval/type_convertor/java_type_converter.py',
         'eval_checker/ast_eval/type_convertor/js_type_converter.py']
manifest = {}
for rel in paths:
    raw = (source/rel).read_bytes()
    text = raw.decode('utf-8').replace('from bfcl_eval.', 'from multilingual_bfcl._vendor.bfcl.')
    path = dest/rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')
    manifest[rel] = {'source_sha256':hashlib.sha256(raw).hexdigest(),
                     'vendored_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    parent = path.parent
    while parent != dest.parent.parent:
        (parent/'__init__.py').touch(exist_ok=True)
        parent = parent.parent
(dest/'SNAPSHOT.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(dest/'LICENSE').write_bytes((ROOT.parent/'LICENSE').read_bytes())
print('Vendored five BFCL modules with import-only changes')
