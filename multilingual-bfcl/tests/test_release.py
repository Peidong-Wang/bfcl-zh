import ast
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from multilingual_bfcl.datasets import benchmark_path,load_jsonl
from multilingual_bfcl.eval_runner import score_entry,score_predictions,decode_calls,run_evaluation
from multilingual_bfcl.inference import request_payload,extract_calls

def first_value(answers, schema):
    value=next((v for v in answers if v!=''),answers[0])
    if isinstance(value,dict):
        return {k:first_value(v,schema.get('properties',{}).get(k,{})) for k,v in value.items()}
    # Array alternatives already contain actual values. Nested dict values are BFCL candidates.
    if isinstance(value,list):
        return [{k:first_value(v,{}) for k,v in item.items()} if isinstance(item,dict) else item for item in value]
    return value

def oracle(entry):
    call=entry['ground_truth'][0]
    name,params=next(iter(call.items()))
    definition=next(f for f in entry['function'] if f['name']==name)['parameters']
    schema=definition['properties']
    return [{name:{k:first_value(v,schema.get(k,{})) for k,v in params.items()
                  if k in definition['required'] or v!=['']}}]

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.path=benchmark_path('bfcl_multiple','zh-CN','zh-CN_translatable_full')
        self.rows=load_jsonl(self.path)

    def test_every_oracle_all_conditions(self):
        for locale,prefix,conditions in [('en','en',['']),('de','de',['_query','_full','_func_desc','_full_func_desc','_full_lang_desc']),('zh-CN','zh-CN',['_query','_full','_func_desc','_full_func_desc','_full_lang_desc'])]:
            for condition in conditions:
                if locale=='de':
                    from multilingual_bfcl.datasets import data_root
                    if not (data_root()/'bfcl_multiple/de').is_dir(): continue
                rows=load_jsonl(benchmark_path('bfcl_multiple',locale,prefix+'_translatable'+condition))
                for r in rows:
                    with self.subTest(locale=locale,condition=condition,id=r['id']):
                        self.assertTrue(score_entry(r,oracle(r))['valid'])

    def test_wrong_function_parameter_count_and_type(self):
        r=self.rows[0]
        for bad in [[],[{'invented':{'country':'巴西'}}],[{'country_info.capital':{'country':'错误'}}],
                    [{'country_info.capital':{}}],[{'country_info.capital':{'country':123}}],
                    oracle(r)+oracle(r)]:
            self.assertFalse(score_entry(r,bad)['valid'])

    def test_inline_chinese_not_english(self):
        self.assertTrue(score_entry(self.rows[0],[{'country_info.capital':{'country':'巴西'}}])['valid'])
        self.assertFalse(score_entry(self.rows[0],[{'country_info.capital':{'country':'Brazil'}}])['valid'])

    def test_api_name_mapping(self):
        calls=decode_calls({'tool_calls':[{'function':{'name':'country_info_capital','arguments':'{"country":"巴西"}'}}]})
        self.assertTrue(score_entry(self.rows[0],calls,'api')['valid'])
        self.assertFalse(score_entry(self.rows[0],calls,'canonical')['valid'])

    def test_payload_all_cases_no_answer_leak_and_schema_conversion(self):
        for row in self.rows:
            for route in ('standard','reasoning','responses','claude'):
                p=request_payload(row,'test',route,512)
                self.assertNotIn('ground_truth',p)
                self.assertNotIn('source_id',p)
                self.assertNotIn('localization_level',p)
                self.assertEqual(len(p['tools']),len(row['function']))
                for tool in p['tools']:
                    schema=tool.get('function',{}).get('parameters',tool.get('parameters',tool.get('input_schema')))
                    self.assertEqual(schema['type'],'object')
                if route=='reasoning':
                    self.assertNotIn('temperature',p)
                    self.assertEqual(p['max_completion_tokens'],512)
        self.assertEqual(extract_calls({'output':[{'type':'function_call','name':'f','arguments':'{}'}]},'responses'),[{'function':{'name':'f','arguments':'{}'}}])

    def test_invalid_prediction_is_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.jsonl'
            p.write_text(json.dumps({'id':self.rows[0]['id'],'tool_calls':[{'function':{'name':'f','arguments':'not json'}}]})+'\n',encoding='utf-8')
            report=score_predictions(self.path,p)
            self.assertFalse(report['results'][0]['valid'])
            self.assertEqual(report['results'][0]['error_type'],'invalid_prediction')

    def test_complete_denominator_missing_errors_and_unknown_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'predictions.jsonl'
            p.write_text(json.dumps({'id':self.rows[0]['id'],'calls':oracle(self.rows[0])},ensure_ascii=False)+'\n',encoding='utf-8')
            report=score_predictions(self.path,p)
            self.assertEqual((report['correct'],report['total'],report['missing']),(1,132,131))
            p.write_text('{"id":"unknown","calls":[]}\n',encoding='utf-8')
            with self.assertRaises(ValueError): score_predictions(self.path,p)
            p.write_text('{"id":"a","calls":[]}\n{"id":"a","calls":[]}\n',encoding='utf-8')
            with self.assertRaises(ValueError): score_predictions(self.path,p)
            p.write_text(json.dumps({'id':self.rows[0]['id'],'api_error':'timeout'})+'\n',encoding='utf-8')
            self.assertEqual(score_predictions(self.path,p)['api_errors'],1)

    def test_require_explicit_condition_and_safe_paths(self):
        with self.assertRaises(ValueError): run_evaluation('test','bfcl_multiple','zh-CN',Path('unused'))
        with self.assertRaises(ValueError): benchmark_path('bfcl_multiple','../en','en_translatable')

    def test_vendored_scoring_logic_matches_snapshot(self):
        root=Path(__file__).resolve().parents[1]
        source=root.parent/'berkeley-function-call-leaderboard/bfcl_eval'
        if not source.exists(): self.skipTest('Upstream source is outside installed package')
        vendor=root/'src/multilingual_bfcl/_vendor/bfcl'
        manifest=json.loads((vendor/'SNAPSHOT.json').read_text())
        for rel,hashes in manifest.items():
            raw=(source/rel).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),hashes['source_sha256'])
            transformed=raw.decode().replace('from bfcl_eval.','from multilingual_bfcl._vendor.bfcl.')
            self.assertEqual(ast.dump(ast.parse(transformed)),ast.dump(ast.parse((vendor/rel).read_text())))

if __name__=='__main__': unittest.main()
