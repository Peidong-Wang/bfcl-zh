import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
oracle_count=sum(1 for locale in ('en','de','zh-CN') for p in (ROOT/'data/benchmarks/bfcl_multiple'/locale).glob('*translatable*.jsonl') for line in p.read_text(encoding='utf-8').splitlines() if line.strip())
report={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'passed':result.wasSuccessful(),'oracle_regressions':oracle_count,
        'real_model_evaluation_run':False,'translation_api_used':False,
        'full_suite_data_complete':json.loads((ROOT/'data/benchmarks/bfcl_full/build_status.json').read_text(encoding='utf-8'))['complete']}
(ROOT/'TEST_REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
sys.exit(not result.wasSuccessful())
