"""Build only categories whose directly authored query translations are complete."""
import copy
import hashlib
import json
import shutil
from pathlib import Path
from prepare_full_suite import OUT,SOURCE,read,prepare

def build():
    prepare()
    translations=json.loads((OUT/'query_translations.json').read_text(encoding='utf-8'))
    target=OUT/'zh-CN'
    target.mkdir(parents=True,exist_ok=True)
    completed=[]
    pending={}
    for source in sorted(SOURCE.glob('BFCL_v4_*.json')):
        if source.stem.endswith('format_sensitivity'):
            shutil.copyfile(source,target/source.name)
            continue
        rows=read(source)
        missing=[]
        translated=copy.deepcopy(rows)
        for row in translated:
            for turn in row.get('question',[]):
                for message in turn:
                    if message.get('role')!='user': continue
                    key=hashlib.sha256(message['content'].encode()).hexdigest()
                    if not translations.get(key): missing.append(key)
                    else: message['content']=translations[key]
        if missing:
            pending[source.stem]=len(set(missing))
            continue
        output=target/source.name
        output.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in translated),encoding='utf-8')
        completed.append({'file':source.name,'records':len(rows),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
    # A QUERY-only condition keeps reference data byte-identical. Never translate
    # execution state or memorized values without synchronizing the scoring system.
    support=[]
    for directory in ('possible_answer','multi_turn_func_doc','memory_prereq_conversation'):
        for source in sorted((SOURCE/directory).rglob('*')):
            if not source.is_file(): continue
            rel=source.relative_to(SOURCE)
            destination=target/rel
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,destination)
            support.append({'file':str(rel).replace('\\','/'),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    report={'scope':'all BFCL v4 registered categories, Chinese user queries with original environment',
            'format_selector_sha256':hashlib.sha256((target/'BFCL_v4_format_sensitivity.json').read_bytes()).hexdigest(),
            'complete':not pending,'completed_physical_categories':completed,'pending_physical_categories':pending,
            'copied_reference_resources':support,'model_evaluation_run':False,'translation_api_used':False}
    (OUT/'build_status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'complete':report['complete'],'completed':[r['file'] for r in completed],
                      'pending_categories':len(pending),'reference_files':len(support)},ensure_ascii=False))

if __name__=='__main__': build()
