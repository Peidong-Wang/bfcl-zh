"""Curate a reproducible source release, excluding credentials and historical runs."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/bfcl-v4-zh-CN-source.zip'

def create():
    if not json.loads((ROOT/'data/benchmarks/bfcl_full/validation.json').read_text(encoding='utf-8'))['publishable']:
        raise RuntimeError('Full-suite validation has not passed')
    files={}
    def add(path,name):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.pyo'):
            files[name]=path
    for name in ('src','tests','data/benchmarks/bfcl_full','data/benchmarks/bfcl_multiple/en','data/benchmarks/bfcl_multiple/zh-CN'):
        for p in (ROOT/name).rglob('*'): add(p,'multilingual-bfcl/'+p.relative_to(ROOT).as_posix())
    scripts=['prepare_full_suite.py','build_full_suite.py','validate_full_suite.py','export_translation_batch.py',
             'build_chinese_benchmark.py','validate_chinese_benchmark.py','run_release_tests.py',
             'prepare_release_metadata.py','vendor_bfcl_checker.py','package_full_suite.py','create_source_release.py',
             'verify_installed_wheel.py']
    for name in scripts: add(ROOT/'scripts'/name,'multilingual-bfcl/scripts/'+name)
    for pattern in ('*.md','*.json','LICENSE','NOTICE','setup.py','pyproject.toml','MANIFEST.in'):
        for p in ROOT.glob(pattern): add(p,'multilingual-bfcl/'+p.name)
    source=ROOT.parent/'berkeley-function-call-leaderboard/bfcl_eval'
    for p in (source/'data').glob('BFCL_v4_*.json'): add(p,'berkeley-function-call-leaderboard/bfcl_eval/data/'+p.name)
    for directory in ('possible_answer','multi_turn_func_doc','memory_prereq_conversation'):
        for p in (source/'data'/directory).rglob('*'):
            add(p,'berkeley-function-call-leaderboard/bfcl_eval/'+p.relative_to(source).as_posix())
    manifest=json.loads((ROOT/'src/multilingual_bfcl/_vendor/bfcl/SNAPSHOT.json').read_text())
    for rel in manifest: add(source/rel,'berkeley-function-call-leaderboard/bfcl_eval/'+rel)
    add(ROOT/'LICENSE','LICENSE')
    add(ROOT/'RELEASE_README.md','README.md')
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('.gitattributes','* -text\n')
        z.writestr('.gitignore','__pycache__/\n*.py[cod]\n*.egg-info/\nbuild/\ndist/\n.env\n.env.*\n!*.example\n.venv/\nvenv/\n')
        for name,path in sorted(files.items()): z.write(path,name)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        assert not any('/.env' in n or 'results_robustness' in n for n in z.namelist())
        for name,path in files.items(): assert z.read(name)==path.read_bytes()
    print(json.dumps({'archive':str(OUT),'files':len(files),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}))

if __name__=='__main__': create()
