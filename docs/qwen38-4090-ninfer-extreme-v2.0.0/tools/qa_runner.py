"""Supplemental Java semantic QA; not a replacement for real Agent tasks."""
import argparse,json,os,re,time
from pathlib import Path
from .http_probe import probe

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--model',required=True);p.add_argument('--out',required=True);p.add_argument('--seed',type=int,default=4090);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];cases=json.loads((root/'fixtures/java-semantics-30.json').read_text());out=Path(a.out);out.mkdir(parents=True,exist_ok=False);out.chmod(0o700);rows=[]
    for n,c in enumerate(cases):
        body={'model':a.model,'messages':[{'role':'user','content':c['prompt']}],'temperature':1.0,'top_p':.95,'top_k':20,'reasoning_effort':'medium','seed':a.seed,'max_tokens':1024}
        try:
            stats,text=probe(a.url,body,120,os.environ.get('LAB_API_KEY'))
            cleaned=re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip())
            try:value=json.loads(cleaned).get('value');ok=value==c['expected_value'];fmt=isinstance(value,str)
            except (ValueError,AttributeError):ok=False;fmt=False
            row={'id':c['id'],'pass':ok and stats['done'] and not stats['http_errors_present'],'format':fmt,'metrics':stats}
        except Exception as e:row={'id':c['id'],'pass':False,'error_type':type(e).__name__}
        rows.append(row);print(f'[{n+1}/30] {c["id"]} pass={row["pass"]}',flush=True)
        (out/'qa-results.json').write_text(json.dumps({'source':'LIVE_HTTP','run_id':os.environ.get('LAB_RUN_ID'),'rows':rows,'complete':len(rows)==30},indent=2)+'\n')
    raise SystemExit(0 if all(x['pass'] for x in rows) else 1)
if __name__=='__main__':main()
