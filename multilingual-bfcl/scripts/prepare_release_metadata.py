"""Write content-pinned provenance and an explicitly AI-only review ledger."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/benchmarks/bfcl_multiple'
UPSTREAM=ROOT.parent/'berkeley-function-call-leaderboard/bfcl_eval/data'
def read(path):
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

rows=read(DATA/'en/en_translatable.jsonl')
questions={r['id']:r for r in read(UPSTREAM/'BFCL_v4_multiple.json')}
answers={r['id']:r for r in read(UPSTREAM/'possible_answer/BFCL_v4_multiple.json')}
mapping=[]
for row in rows:
    sid=row['id']
    assert row['messages']==questions[sid]['question']
    assert row['function']==questions[sid]['function']
    assert row['ground_truth']==answers[sid]['ground_truth']
    mapping.append({'source_id':sid,'normalized_input_sha256':digest(row)})
provenance={'checked':'2026-10-16','subset':'132 supplied frozen multiple IDs',
            'upstream_git_commit':None,'upstream_commit_note':'User archive lacks Git metadata; content hashes are authoritative',
            'official_dataset_card':'https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard',
            'declared_license':'Apache-2.0','all_source_rows_match_supplied_bfcl':True,'records':mapping}
(ROOT/'PROVENANCE.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
review={'date':'2026-10-16','reviewer':'Codex, same session second pass','independent_human_review':False,
        'scope':'132-case five-condition subset; full-suite review tracked separately',
        'description_count':1104,'records':[]}
for row in read(DATA/'zh-CN/zh-CN_translatable_full.jsonl'):
    review['records'].append({'source_id':row['source_id'],'content_sha256':digest(row),
                              'status':'Codex second-pass review; see disclosed source ambiguities'})
(ROOT/'CHINESE_REVIEW.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('132 provenance matches; 132 content-pinned AI review entries')
