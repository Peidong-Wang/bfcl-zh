"""Rebuild the five Chinese conditions offline from reviewed translation assets."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from multilingual_bfcl.localization.translator import add_language_descriptors_to_entry

BASE = ROOT / 'data/benchmarks/bfcl_multiple'
OUT = BASE / 'zh-CN'

def load(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def description_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'description':
                yield item
            else:
                yield from description_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from description_strings(item)

def replace_descriptions(value, translations):
    if isinstance(value, dict):
        return {k: translations[v] if k == 'description' else replace_descriptions(v, translations) for k,v in value.items()}
    if isinstance(value, list):
        return [replace_descriptions(v, translations) for v in value]
    return value

def translated_values(value, mapping, schema=None, param=None):
    schema = schema or {}
    # Enum tokens, defaults, identifiers, keys and numeric/date values stay fixed.
    if 'enum' in schema:
        return copy.deepcopy(value)
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        # BFCL wraps alternatives in lists: preserve shape and all alternatives.
        child = schema.get('items', schema) if schema.get('type') == 'array' else schema
        return [translated_values(v, mapping, child, param) for v in value]
    if isinstance(value, dict):
        props = schema.get('properties', {})
        return {k: translated_values(v, mapping, props.get(k, {}), k) for k,v in value.items()}
    return value

def build():
    source = BASE / 'en/en_translatable.jsonl'
    # Ordered description assets were reviewed against this exact source snapshot.
    assert hashlib.sha256(source.read_bytes()).hexdigest() == 'badafe2952c617167d1c71d572562a5f588475d028f15c463883b947cb44146d', 'English source changed; review translation alignment before rebuilding'
    rows = load(source)
    queries = dict(line.split('\t', 1) for line in (OUT/'queries.tsv').read_text(encoding='utf-8').splitlines())
    values = json.loads((OUT/'values.json').read_text(encoding='utf-8'))
    originals = list(dict.fromkeys(description_strings([r['function'] for r in rows])))
    translated = []
    for name in ['descriptions_zh.txt','descriptions_zh_2.txt','descriptions_zh_3.txt','descriptions_zh_4.txt']:
        translated.extend((OUT/name).read_text(encoding='utf-8').splitlines())
    assert len(originals) == len(translated), (len(originals),len(translated))
    assert len(rows) == len(queries) == 132
    descriptions = dict(zip(originals, translated))
    outputs = {k: [] for k in ['query','full','func_desc','full_func_desc','full_lang_desc']}
    for original in rows:
        sid = original['id']
        query = copy.deepcopy(original)
        query.update(id=f'{sid}_zh-CN', source_id=sid, locale='zh-CN', localization_level='query')
        assert len(query['messages']) == 1 and len(query['messages'][0]) == 1
        query['messages'][0][0]['content'] = queries[sid.split('_')[-1]]
        full = copy.deepcopy(query)
        full['localization_level'] = 'full'
        functions = {f['name']: f for f in original['function']}
        full['ground_truth'] = []
        for call in original['ground_truth']:
            new_call = {}
            for name, params in call.items():
                schemas = functions[name]['parameters'].get('properties',{})
                mapped = {}
                for param, alternatives in params.items():
                    local_map = values.copy()
                    # Preserve literal translation input and configured model names.
                    if sid == 'multiple_67' and param == 'text':
                        local_map = {}
                    if sid == 'multiple_114' and param == 'model':
                        local_map = {}
                    if sid == 'multiple_56' and param == 'data_source':
                        local_map = {}
                    if sid == 'multiple_66' and param == 'time_period':
                        local_map = {}  # Documented selector tokens 'now'/'weekend'.
                    if sid == 'multiple_168' and param == 'artist_name':
                        local_map['Queen'] = '皇后乐队'
                    if param in {'username','snp_id','case_number','docket','table','field','operation'}:
                        local_map = {}
                    mapped[param] = translated_values(alternatives,local_map,schemas.get(param,{}),param)
                new_call[name] = mapped
                # The text itself is Chinese in FULL, so its language must agree.
                if sid == 'multiple_149':
                    new_call[name]['language'] = ['中文', '汉语']
            full['ground_truth'].append(new_call)
        desc = copy.deepcopy(query)
        desc['messages'] = copy.deepcopy(original['messages'])
        desc['function'] = replace_descriptions(original['function'],descriptions)
        desc['localization_level'] = 'function_descriptions'
        combined = copy.deepcopy(full)
        combined['function'] = copy.deepcopy(desc['function'])
        combined['localization_level'] = 'full_and_function_descriptions'
        hint = copy.deepcopy(full)
        add_language_descriptors_to_entry(hint,'English, Chinese (Simplified)')
        for key,record in zip(outputs,[query,full,desc,combined,hint]):
            outputs[key].append(record)
    manifest = {'locale':'zh-CN','status':'draft','source':str(source.relative_to(ROOT)).replace('\\','/'),
                'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'translation_method':'Codex-authored static translations; deterministic offline reconstruction; no translation API called',
                'unique_descriptions':len(originals),'files':{}}
    for condition, records in outputs.items():
        path = OUT/f'zh-CN_translatable_{condition}.jsonl'
        path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
        manifest['files'][path.name] = {'records':len(records),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        print(path.name,len(records))
    (OUT/'build_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__ == '__main__':
    build()
