"""Offline structural and reproducibility checks; not a linguistic certification."""
from __future__ import annotations
import ast
import collections
import hashlib
import json
import re
from pathlib import Path
from build_chinese_benchmark import BASE, OUT, ROOT, build, load, description_strings

def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k,v in value.items()}
    if isinstance(value, list):
        return [shape(v) for v in value]
    return '<string>' if isinstance(value,str) else (type(value).__name__,value)

def strip_descriptions(value):
    if isinstance(value,dict):
        return {k:strip_descriptions(v) for k,v in value.items() if k!='description'}
    if isinstance(value,list):
        return [strip_descriptions(v) for v in value]
    return value

def validate():
    source = load(BASE/'en/en_translatable.jsonl')
    ids = [r['id'] for r in source]
    assert len(ids) == len(set(ids)) == 132
    outputs = {key:load(OUT/f'zh-CN_translatable_{key}.jsonl') for key in
               ['query','full','func_desc','full_func_desc','full_lang_desc']}
    de_path=BASE/'de/de_translatable_full.jsonl'
    de_ids = [r['source_id'] for r in load(de_path)] if de_path.exists() else ids
    assert ids == de_ids
    manifest = json.loads((OUT/'build_manifest.json').read_text(encoding='utf-8'))
    assert manifest['source_sha256'] == hashlib.sha256((BASE/'en/en_translatable.jsonl').read_bytes()).hexdigest()
    for name, data in outputs.items():
        assert len(data) == 132
        assert [r['source_id'] for r in data] == ids
        assert len({r['id'] for r in data}) == 132
        for i,r in enumerate(data):
            original = source[i]
            assert r['id'] == f'{ids[i]}_zh-CN' and r['locale']=='zh-CN'
            assert shape(r['ground_truth']) == shape(original['ground_truth'])
            assert strip_descriptions(r['function']) == strip_descriptions(original['function'])
            assert shape(r['messages']) == shape(original['messages'])
            if name in {'query','func_desc'}:
                assert r['ground_truth'] == original['ground_truth']
            if name in {'query','full'}:
                assert r['function'] == original['function']
            if name == 'func_desc':
                assert r['messages'] == original['messages']
            else:
                assert re.search(r'[\u3400-\u9fff]',r['messages'][0][0]['content'])
            if name in {'func_desc','full_func_desc'}:
                assert all(re.search(r'[\u3400-\u9fff]',s) for s in description_strings(r['function']))
        path = OUT/f'zh-CN_translatable_{name}.jsonl'
        assert manifest['files'][path.name]['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    for q,f,d,c,h in zip(*(outputs[k] for k in ['query','full','func_desc','full_func_desc','full_lang_desc'])):
        assert q['messages'] == f['messages'] == c['messages'] == h['messages']
        assert c['function'] == d['function']
        assert f['ground_truth'] == c['ground_truth'] == h['ground_truth']
    assert any('Languages: English, Chinese (Simplified).' in json.dumps(h['function']) for h in outputs['full_lang_desc'])
    full = {r['source_id']:r for r in outputs['full']}
    assert full['multiple_67']['ground_truth'][0]['translate']['text'] == ['Hello, how are you?']
    assert full['multiple_149']['ground_truth'][0]['sentiment_analysis']['language'] == ['中文','汉语']
    assert full['multiple_180']['ground_truth'][0]['game_stats.fetch_player_statistics']['username'] == ['Sam']
    assert full['multiple_168']['ground_truth'][0]['get_song_lyrics']['artist_name'] == ['皇后乐队']
    before = {p.name:p.read_bytes() for p in OUT.glob('*.jsonl')}
    build()
    assert before == {p.name:p.read_bytes() for p in OUT.glob('*.jsonl')}
    groups = collections.defaultdict(list)
    for row in source:
        signature = json.dumps({'messages':row['messages'],'function':row['function']},sort_keys=True,ensure_ascii=False)
        groups[signature].append(row['id'])
    duplicates = [g for g in groups.values() if len(g)>1]
    parsed = 0
    errors = []
    for path in sorted((ROOT/'data').rglob('*.jsonl')):
        for lineno,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
            if not line.strip(): continue
            try: json.loads(line); parsed += 1
            except json.JSONDecodeError: errors.append(f'{path.relative_to(ROOT)}:{lineno}')
    syntax_errors=[]
    for path in sorted(ROOT.rglob('*.py')):
        try: ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        except SyntaxError as e: syntax_errors.append(f'{path.relative_to(ROOT)}:{e.lineno}')
    query_groups = collections.defaultdict(list)
    for row in source:
        query_groups[json.dumps(row['messages'],ensure_ascii=False)].append(row['id'])
    full_status=json.loads((ROOT/'data/benchmarks/bfcl_full/validation.json').read_text(encoding='utf-8'))
    ready=full_status['publishable'] and not errors and not syntax_errors
    result = {'chinese_structural_checks':'passed','rebuild_byte_identical':True,
              'conditions':len(outputs),'records_per_condition':132,'distinct_input_structures':len(groups),
              'duplicate_input_groups':duplicates,'data_jsonl_records_parsed':parsed,'data_jsonl_errors':errors,
              'repeated_query_groups':[g for g in query_groups.values() if len(g)>1],
              'multilingual_package_syntax_errors':syntax_errors,
              'limitations':['No independent human review','No real model baseline (not required by user)'],
              'release_blockers':[] if ready else ['Full-suite integrity checks must pass'],
              'release_ready':ready,'scope':'data and software integrity; hosting status is separate'}
    (ROOT/'VALIDATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not errors and not syntax_errors

if __name__ == '__main__':
    validate()
