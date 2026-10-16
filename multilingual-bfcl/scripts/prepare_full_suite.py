"""Inventory the complete supplied BFCL v4 snapshot, without LLM/API calls.

Build a deduplicated translation ledger. A missing Chinese translation is never
silently replaced by English or marked complete. Query-only localization keeps
tool definitions, expected answers, prerequisite memory and state unchanged.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'berkeley-function-call-leaderboard/bfcl_eval/data'
OUT=ROOT/'data/benchmarks/bfcl_full'

def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    units={}
    categories=[]
    for path in sorted(SOURCE.glob('BFCL_v4_*.json')):
        category=path.stem.removeprefix('BFCL_v4_')
        if category=='format_sensitivity': continue
        rows=read(path)
        answer=SOURCE/'possible_answer'/path.name
        answer_ids={r['id'] for r in read(answer)} if answer.exists() else set()
        for row in rows:
            for ti,turn in enumerate(row.get('question',[])):
                for mi,message in enumerate(turn):
                    if message.get('role')!='user': continue
                    text=message['content']
                    key=hashlib.sha256(text.encode()).hexdigest()
                    item=units.setdefault(key,{'key':key,'source':text,'uses':[]})
                    item['uses'].append({'category':category,'id':row['id'],'turn':ti,'message':mi})
        categories.append({'physical_category':category,'records':len(rows),
                           'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                           'answer_file':str(answer.relative_to(SOURCE)).replace('\\','/') if answer.exists() else None,
                           'missing_answer_ids':sorted({r['id'] for r in rows}-answer_ids) if answer.exists() else [],
                           'answer_mode':'no fixed AST answers by design' if not answer.exists() else 'separate answer file'})
    assets=OUT/'query_translations.json'
    # Reconstruct from authored assets every time; never trust stale generated cache.
    translations={}
    # Seed directly authored existing query translations, shared across categories.
    en=read(ROOT/'data/benchmarks/bfcl_multiple/en/en_translatable.jsonl')
    zh=read(ROOT/'data/benchmarks/bfcl_multiple/zh-CN/zh-CN_translatable_query.jsonl')
    for a,b in zip(en,zh):
        source=a['messages'][0][0]['content']
        translations.setdefault(hashlib.sha256(source.encode()).hexdigest(),b['messages'][0][0]['content'])
    memory_asset=OUT/'memory_queries_zh.txt'
    if memory_asset.exists():
        source_rows=read(SOURCE/'BFCL_v4_memory.json')
        chinese=memory_asset.read_text(encoding='utf-8').splitlines()
        assert len(source_rows)==len(chinese)==155
        for row,text in zip(source_rows,chinese):
            assert text.strip()
            original=row['question'][0][0]['content']
            translations[hashlib.sha256(original.encode()).hexdigest()]=text
    for patch in sorted(OUT.glob('*_query_additions.tsv')):
        category=patch.name.removesuffix('_query_additions.tsv')
        source_rows={r['id']:r for r in read(SOURCE/f'BFCL_v4_{category}.json')}
        for line in patch.read_text(encoding='utf-8').splitlines():
            parts=line.split('\t',2)
            sid=parts[0]
            ordinal=int(parts[1]) if len(parts)==3 else None
            chinese=parts[-1]
            row=source_rows[sid]
            user_messages=[m for t in row['question'] for m in t if m.get('role')=='user']
            if ordinal is None:
                assert len(user_messages)==1, f'{sid}: provide explicit user-message ordinal'
                ordinal=0
            original=user_messages[ordinal]['content']
            translations[hashlib.sha256(original.encode()).hexdigest()]=chinese
    for batch in sorted((OUT/'authored_batches').glob('*_source.json')):
        zh_path=batch.with_name(batch.name.removesuffix('_source.json')+'_zh.txt')
        if not zh_path.exists(): continue
        originals=json.loads(batch.read_text(encoding='utf-8'))
        chinese=zh_path.read_text(encoding='utf-8').splitlines()
        assert len(originals)==len(chinese), f'{batch.name}: translation line count mismatch'
        for original,translation in zip(originals,chinese):
            assert hashlib.sha256(original['source'].encode()).hexdigest()==original['key']
            assert original['key'] in units and translation.strip()
            translations[original['key']]=translation
    # JSON overrides preserve authored real newlines separately from literal escapes.
    for patch in sorted((OUT/'authored_batches').glob('*_translations.json')):
        for key,translation in json.loads(patch.read_text(encoding='utf-8')).items():
            assert key in units and isinstance(translation,str) and translation.strip()
            translations[key]=translation
    assets.write_text(json.dumps(translations,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    invariant_file=OUT/'invariant_queries.json'
    invariants=json.loads(invariant_file.read_text(encoding='utf-8')) if invariant_file.exists() else {}
    for patch in sorted((OUT/'authored_batches').glob('*_invariants.json')):
        content=json.loads(patch.read_text(encoding='utf-8'))
        if isinstance(content,list): content={r['source']:r['reason'] for r in content}
        else: content={v['source'] if isinstance(v,dict) else k:v['reason'] if isinstance(v,dict) else v for k,v in content.items()}
        invariants.update(content)
    invariant_file.write_text(json.dumps(invariants,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    ledger=[]
    for item in units.values():
        item['translation']=translations.get(item['key'])
        item['status']='translated_pending_full_suite_review' if item['translation'] else 'pending'
        if item['source'] in invariants:
            assert item['translation']==item['source'], 'Invariant code was modified'
            item['status']='reviewed_invariant_code'
            item['invariant_reason']=invariants[item['source']]
        ledger.append(item)
    (OUT/'query_ledger.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in ledger),encoding='utf-8')
    manifest={'snapshot':'user-supplied BFCL_v4','scope':'all registered v4 categories; query-only localization',
              'physical_jsonl_categories':len(categories),'logical_categories':23,'logical_scoring_categories':22,
              'physical_source_records':sum(c['records'] for c in categories),
              'logical_scoring_records_after_memory_and_web_variants':5106,
              'format_sensitivity':'200 IDs selecting existing cases; not an extra independent question set',
              'unique_query_strings':len(units),'translated_unique_queries':sum(bool(i['translation']) for i in ledger),
              'remaining_unique_queries':sum(not i['translation'] for i in ledger),
              'reviewed_invariant_queries':sum(i['status']=='reviewed_invariant_code' for i in ledger),
              'complete':all(i['translation'] for i in ledger),'categories':categories,
              'translation_method':'direct Codex authoring; no translation API; no model evaluation',
              'state_policy':'retain all original keys, code, fixed tokens, tools, answers and initial/prerequisite state'}
    (OUT/'inventory.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='categories'},ensure_ascii=False,indent=2))

if __name__=='__main__': prepare()
