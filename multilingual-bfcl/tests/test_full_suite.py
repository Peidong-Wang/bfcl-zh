import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FULL=ROOT/'data/benchmarks/bfcl_full'
SOURCE=ROOT.parent/'berkeley-function-call-leaderboard/bfcl_eval/data'

class FullSuiteTests(unittest.TestCase):
    def test_resource_api_rejects_traversal(self):
        from multilingual_bfcl.datasets import full_category_path
        for category in ('../memory','MEMORY','memory.json','a/b',''):
            with self.assertRaises(ValueError): full_category_path(category)

    def test_completed_categories_keep_answers_state_and_ids(self):
        if not (FULL/'build_status.json').exists(): self.skipTest('Full suite is outside subset wheel')
        status=json.loads((FULL/'build_status.json').read_text(encoding='utf-8'))
        invariants=json.loads((FULL/'invariant_queries.json').read_text(encoding='utf-8'))
        for item in status['completed_physical_categories']:
            load=lambda p:[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
            en=load(SOURCE/item['file'])
            zh=load(FULL/'zh-CN'/item['file'])
            self.assertEqual(len(en),len(zh))
            for original,translated in zip(en,zh):
                for key in original:
                    if key!='question': self.assertEqual(original[key],translated[key])
                self.assertEqual(len(original['question']),len(translated['question']))
                for a,b in zip(original['question'],translated['question']):
                    self.assertEqual(len(a),len(b))
                    for before,after in zip(a,b):
                        self.assertEqual(before['role'],after['role'])
                        if before['role']=='user':
                            if before['content'] in invariants: self.assertEqual(before,after)
                            else: self.assertRegex(after['content'],r'[\u3400-\u9fff]')
                        else: self.assertEqual(before,after)

    def test_reference_files_byte_identical_and_no_false_complete(self):
        if not (FULL/'build_status.json').exists(): self.skipTest('Full suite is outside subset wheel')
        status=json.loads((FULL/'build_status.json').read_text(encoding='utf-8'))
        self.assertEqual(status['complete'],not bool(status['pending_physical_categories']))
        for item in status['copied_reference_resources']:
            self.assertEqual((SOURCE/item['file']).read_bytes(),(FULL/'zh-CN'/item['file']).read_bytes())
        actual={p.name for p in (FULL/'zh-CN').glob('BFCL_v4_*.json') if 'format_sensitivity' not in p.name}
        self.assertEqual(actual,{r['file'] for r in status['completed_physical_categories']})

if __name__=='__main__': unittest.main()
