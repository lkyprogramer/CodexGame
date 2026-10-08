import argparse,json
from pathlib import Path
from .artifact import inspect_artifact,sha256_file
from .metrics import aggregate_rounds,candidate_gate

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
    a=s.add_parser('artifact');a.add_argument('path');a.add_argument('--hash',action='store_true')
    a=s.add_parser('rounds');a.add_argument('path')
    a=s.add_parser('gate');a.add_argument('path')
    args=p.parse_args()
    if args.cmd=='artifact':
        r=inspect_artifact(args.path)
        if args.hash:r['sha256']=sha256_file(args.path)
    elif args.cmd=='rounds':r=aggregate_rounds([json.loads(l) for l in Path(args.path).read_text().splitlines() if l.strip()])
    else:r=candidate_gate(json.loads(Path(args.path).read_text()))
    print(json.dumps(r,ensure_ascii=False,indent=2))
    if args.cmd=='gate' and r['verdict']!='CANDIDATE_PASS_NOT_RELEASED':raise SystemExit(2)
if __name__=='__main__':main()
