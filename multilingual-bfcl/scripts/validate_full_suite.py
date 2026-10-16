"""Check full-suite coverage separately from the integrity of completed categories."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from prepare_full_suite import OUT,SOURCE,read

def validate(require_complete=False):
    status=json.loads((OUT/'build_status.json').read_text(encoding='utf-8'))
    inventory=json.loads((OUT/'inventory.json').read_text(encoding='utf-8'))
    invariants=json.loads((OUT/'invariant_queries.json').read_text(encoding='utf-8'))
    errors=[]
    technical_flags=[]
    reviewed_records=0
    all_ids=set()
    def check(test,detail):
        if not test: errors.append(detail)
    for item in inventory['categories']:
        source=SOURCE/f'BFCL_v4_{item["physical_category"]}.json'
        check(hashlib.sha256(source.read_bytes()).hexdigest()==item['source_sha256'],f'Source changed: {source.name}')
        records=read(source)
        check(len(records)==item['records'],f'Count changed: {source.name}')
        check(len({r['id'] for r in records})==len(records),f'Duplicate IDs: {source.name}')
        all_ids.update(r['id'] for r in records)
        check(not item['missing_answer_ids'],f'Missing answer IDs: {source.name}')
    for item in status['completed_physical_categories']:
        name=item['file']
        original=read(SOURCE/name)
        translated=read(OUT/'zh-CN'/name)
        check(len(original)==len(translated),f'Count mismatch: {name}')
        check([r['id'] for r in original]==[r['id'] for r in translated],f'ID/order mismatch: {name}')
        for before,after in zip(original,translated):
            sid=before['id']
            check(set(before)==set(after),f'Fields changed: {sid}')
            check({k:v for k,v in before.items() if k!='question'}=={k:v for k,v in after.items() if k!='question'},f'State/tools changed: {sid}')
            check(len(before['question'])==len(after['question']),f'Turn count changed: {sid}')
            for ti,(a,b) in enumerate(zip(before['question'],after['question'])):
                check(len(a)==len(b),f'Message count changed: {sid}/{ti}')
                for mi,(left,right) in enumerate(zip(a,b)):
                    label=f'{sid}/{ti}/{mi}'
                    check({k:v for k,v in left.items() if k!='content'}=={k:v for k,v in right.items() if k!='content'},f'Message metadata changed: {label}')
                    if left.get('role')!='user':
                        check(left==right,f'Non-user message changed: {label}')
                        continue
                    en,zh=left['content'],right['content']
                    check(bool(re.search(r'[\u3400-\u9fff]',zh)) or en in invariants and zh==en,f'Missing Chinese prose: {label}')
                    for literal in re.findall(r'`([^`\n]+)`',en):
                        if literal not in zh:
                            technical_flags.append({'message':label,'literal':literal,'kind':'backtick literal'})
                    for literal in re.findall(r"['\"]([^'\"\n]+)['\"]",en):
                        technical=bool(re.match(r'^(?:https?://|[A-Za-z]:[/\\]|~/|/[A-Za-z])',literal))
                        technical=technical or bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+',literal))
                        if technical and literal not in zh:
                            technical_flags.append({'message':label,'literal':literal,'kind':'quoted path/qualified identifier'})
            reviewed_records+=1
        check(hashlib.sha256((OUT/'zh-CN'/name).read_bytes()).hexdigest()==item['sha256'],f'Output checksum changed: {name}')
    for resource in status['copied_reference_resources']:
        source=SOURCE/resource['file']
        target=OUT/'zh-CN'/resource['file']
        check(source.read_bytes()==target.read_bytes(),f'Reference modified: {resource["file"]}')
    selector=json.loads((SOURCE/'BFCL_v4_format_sensitivity.json').read_text(encoding='utf-8'))
    selected=[sid for values in selector.values() for sid in values]
    check(set(selected)<=all_ids,'Format selector refers to absent source cases')
    check((SOURCE/'BFCL_v4_format_sensitivity.json').read_bytes()==(OUT/'zh-CN/BFCL_v4_format_sensitivity.json').read_bytes(),'Format selector changed')
    actual={p.name for p in (OUT/'zh-CN').glob('BFCL_v4_*.json') if not p.stem.endswith('format_sensitivity')}
    check(actual=={item['file'] for item in status['completed_physical_categories']},'Stale/untracked category outputs')
    check(status['complete']==(not bool(status['pending_physical_categories'])),'Inconsistent complete status')
    report={'completed_category_integrity':'passed' if not errors else 'failed',
            'full_suite_complete':status['complete'],'completed_physical_categories':len(actual),
            'pending_physical_categories':len(status['pending_physical_categories']),
            'records_checked':reviewed_records,'source_records':inventory['physical_source_records'],
            'remaining_unique_user_texts':inventory['remaining_unique_queries'],
            'format_selection_ids':len(selected),'reference_files_checked':len(status['copied_reference_resources']),
            'errors':errors,'technical_literal_flags':technical_flags,
            'translation_api_used':False,'model_evaluation_run':False,
            'publishable':status['complete'] and not errors and not technical_flags}
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='technical_literal_flags'},ensure_ascii=False,indent=2))
    print(f'Technical literal flags: {len(technical_flags)}')
    return not errors and not technical_flags and (status['complete'] or not require_complete)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    raise SystemExit(0 if validate(args.require_complete) else 1)
