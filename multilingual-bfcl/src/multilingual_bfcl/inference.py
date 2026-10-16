"""One request per case. Standard-library Azure/OpenAI-compatible HTTP transport."""
from __future__ import annotations
import copy
import hashlib
import json
import os
import time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from .datasets import benchmark_path,load_jsonl
from .eval_runner import score_predictions

def json_schema(schema):
    out=copy.deepcopy(schema)
    kind=out.get('type')
    if kind=='any': out.pop('type',None)
    elif kind in {'dict','float','tuple'}: out['type']={'dict':'object','float':'number','tuple':'array'}[kind]
    if 'properties' in out: out['properties']={k:json_schema(v) for k,v in out['properties'].items()}
    if isinstance(out.get('items'),dict): out['items']=json_schema(out['items'])
    return out

def request_payload(entry,model,model_type,max_tokens):
    tools=[]
    names=set()
    for f in entry['function']:
        name=f['name'].replace('.','_')
        if name in names or len(name)>64: raise ValueError('API function name collision/length violation')
        names.add(name)
        tools.append({'type':'function','function':{'name':name,'description':f['description'],
                       'parameters':json_schema(f['parameters'])}})
    messages=[copy.deepcopy(m) for turn in entry['messages'] for m in turn]
    system='Use the supplied tools to answer the user request.'
    if model_type=='claude':
        return {'model':model,'system':system,'messages':messages,'max_tokens':max_tokens,
                'tools':[{'name':t['function']['name'],'description':t['function']['description'],
                          'input_schema':t['function']['parameters']} for t in tools]}
    if model_type=='responses':
        return {'model':model,'instructions':system,'input':messages,'max_output_tokens':max_tokens,
                'tools':[{'type':'function',**t['function']} for t in tools]}
    payload={'model':model,'messages':[{'role':'system','content':system},*messages],'tools':tools}
    if model_type=='reasoning': payload['max_completion_tokens']=max_tokens
    else: payload.update(temperature=0,max_tokens=max_tokens)
    return payload

def extract_calls(response,model_type):
    if model_type=='claude':
        return [{'function':{'name':c['name'],'arguments':c['input']}} for c in response.get('content',[]) if c.get('type')=='tool_use']
    if model_type=='responses':
        return [{'function':{'name':c['name'],'arguments':c['arguments']}} for c in response.get('output',[]) if c.get('type')=='function_call']
    return response['choices'][0]['message'].get('tool_calls',[])

def load_env(path):
    """Read a plain KEY=value file without printing or executing its contents."""
    if not path: return
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        key,sep,value=line.partition('=')
        if not sep or key.strip() not in {'AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_API_KEY','AZURE_OPENAI_DEPLOYMENT'}: continue
        os.environ.setdefault(key.strip(),value.strip().strip('\"\''))

def run(args):
    path=benchmark_path(args.category,args.locale,args.benchmark)
    rows=load_jsonl(path)
    rows=rows[:args.limit] if args.limit else rows
    if args.dry_run:
        return {'selected':len(rows),'payload':request_payload(rows[0],args.model,args.model_type,args.max_tokens)}
    load_env(args.env_file)
    endpoint=os.getenv('AZURE_OPENAI_ENDPOINT','').rstrip('/')
    key=os.getenv('AZURE_OPENAI_API_KEY','')
    if not endpoint or not key: raise ValueError('Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY locally')
    if not endpoint.startswith('https://'): raise ValueError('HTTPS endpoint required')
    # Accept resource root or the exact v1 base URL; retain custom provider prefixes.
    if args.model_type=='claude':
        root=endpoint.removesuffix('/openai/v1').removesuffix('/anthropic')
        url=root+'/anthropic/v1/messages'
        headers={'x-api-key':key,'anthropic-version':'2023-06-01'}
    else:
        base=endpoint if endpoint.endswith('/v1') else endpoint+'/openai/v1'
        url=base+('/responses' if args.model_type=='responses' else '/chat/completions')
        headers={'Authorization':'Bearer '+key}
    out=args.output_dir
    out.mkdir(parents=True,exist_ok=False)  # Refuse mixing runs or silently overwriting.
    selected=out/'selected_benchmark.jsonl'
    selected.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    predictions=out/'predictions.jsonl'
    usage=[]
    with predictions.open('w',encoding='utf-8') as stream:
        for i,entry in enumerate(rows,1):
            payload=request_payload(entry,args.model,args.model_type,args.max_tokens)
            start=time.monotonic()
            try:
                req=Request(url,json.dumps(payload).encode('utf-8'),headers={**headers,'Content-Type':'application/json'})
                with urlopen(req,timeout=args.timeout) as response: result=json.load(response)
                record={'id':entry['id'],'tool_calls':extract_calls(result,args.model_type)}
                usage.append({'id':entry['id'],'usage':result.get('usage',{}),'elapsed_seconds':time.monotonic()-start,
                              'response_model':result.get('model'),'response_id':result.get('id')})
            except (HTTPError,URLError,TimeoutError,ValueError,KeyError) as exc:
                # Do not save response bodies: provider errors may echo sensitive metadata.
                record={'id':entry['id'],'api_error':type(exc).__name__,'status':getattr(exc,'code',None)}
            stream.write(json.dumps(record,ensure_ascii=False)+'\n'); stream.flush()
            print(f'{i}/{len(rows)}',flush=True)
            if record.get('api_error') and i==1:
                raise RuntimeError('First request failed; stopped without retry. Inspect predictions.jsonl and configuration.')
    report=score_predictions(selected,predictions,name_style='api')
    report.update(model=args.model,model_type=args.model_type,max_tokens=args.max_tokens,
                  source_benchmark_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  utc_time=datetime.now(timezone.utc).isoformat(),temperature=0 if args.model_type=='standard' else None,
                  max_requests_per_case=1,system_prompt='Use the supplied tools to answer the user request.',usage=usage)
    (out/'scores.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {k:v for k,v in report.items() if k not in {'results','usage'}}
