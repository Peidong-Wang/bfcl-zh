"""Install locally into a fresh venv and test outside the source tree, offline."""
import hashlib
import json
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
wheel=ROOT/'dist/multilingual_bfcl-0.2.0rc1-py3-none-any.whl'
verification=ROOT.parent.parent/'wheel-verification-full'
verification.mkdir(exist_ok=True)
environment=verification/'venv'
if environment.exists():
    raise RuntimeError('Use a fresh verification directory to avoid reusing an environment')
venv.EnvBuilder(with_pip=True).create(environment)
python=environment/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
subprocess.run([str(python),'-I','-m','pip','install','--no-index','--no-deps',str(wheel)],check=True,cwd=verification)
code="""
import json,pathlib,tempfile
import multilingual_bfcl
from multilingual_bfcl.datasets import benchmark_path,load_jsonl,data_root
from multilingual_bfcl.eval_runner import score_predictions
p=benchmark_path('bfcl_multiple','zh-CN','zh-CN_translatable_full')
rows=load_jsonl(p)
assert len(rows)==132
assert 'site-packages' in str(p)
assert not (data_root()/'bfcl_multiple/de').exists()
assert not (data_root()/'wildtoolbench').exists()
prediction=pathlib.Path('prediction.jsonl')
prediction.write_text(json.dumps({'id':rows[0]['id'],'calls':[{'country_info.capital':{'country':'巴西'}}]},ensure_ascii=False)+'\\n',encoding='utf-8')
r=score_predictions(p,prediction)
assert (r['correct'],r['total'],r['missing'])==(1,132,131)
print(json.dumps({'installed_module':multilingual_bfcl.__file__,'records':len(rows),'correct':r['correct'],'total':r['total']}))
"""
result=subprocess.run([str(python),'-I','-c',code],check=True,cwd=verification,capture_output=True,text=True,encoding='utf-8')
subprocess.run([str(python),'-I','-m','multilingual_bfcl','validate'],check=True,cwd=verification)
subprocess.run([str(python),'-I','-m','multilingual_bfcl','full-validate'],check=True,cwd=verification)
with zipfile.ZipFile(wheel) as z:
    names=z.namelist()
    assert not any(any(part in name for part in ('results_robustness','langasync_jobs','wildtoolbench','/de/','/he/','.env')) for name in names)
    expected=ROOT/'data/benchmarks/bfcl_multiple'
    count=0
    for locale in ('en','zh-CN'):
        for path in (expected/locale).glob('*.jsonl'):
            archived=z.read(f'multilingual_bfcl/data/benchmarks/bfcl_multiple/{locale}/{path.name}')
            assert archived==path.read_bytes()
            count+=1
    full_count=0
    for path in (ROOT/'data/benchmarks/bfcl_full/zh-CN').rglob('*'):
        if path.is_file():
            archived=z.read('multilingual_bfcl/data/benchmarks/bfcl_full/zh-CN/'+path.relative_to(ROOT/'data/benchmarks/bfcl_full/zh-CN').as_posix())
            assert archived==path.read_bytes()
            full_count+=1
report={'wheel':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
        'network_used':False,'isolated_python':True,'clean_venv':True,'outside_source_tree':True,
        'runtime_dependencies':[],'installed_read_and_score':'passed','packaged_jsonl_files_verified':count,
        'excluded_historical_data':'passed','scope':'full BFCL v4 query-only Chinese suite plus 132-case paired experiment',
        'full_suite_files_byte_verified':full_count,
        'installed_check':json.loads(result.stdout)}
(ROOT/'PACKAGING_VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
