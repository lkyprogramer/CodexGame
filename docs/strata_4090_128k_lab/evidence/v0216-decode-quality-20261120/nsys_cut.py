import json, sqlite3, subprocess, sys
from pathlib import Path
NSYS='/usr/local/cuda-12.3/bin/nsys'
res={}
for d in sorted(Path(sys.argv[1]).glob('0*')):
    row=json.loads((d/'ROW.json').read_text()); db=d/'cut.sqlite'
    subprocess.run([NSYS,'export','--type=sqlite','--force-overwrite=true','--output='+str(db),str(d/'trace.nsys-rep')],check=True,capture_output=True,timeout=3600)
    con=sqlite3.connect(str(db)); t0=con.execute('select utcEpochNs from TARGET_INFO_SESSION_START_TIME').fetchone()[0]
    names=dict(con.execute('select id,value from StringIds')); out={}
    for tag,(a,b) in row['marks'].items():
        leg=row['legs'][tag+'-decode']; lo=int((a+leg['first_s'])*1e9)-t0; hi=int(b*1e9)-t0
        ks=con.execute('select start,end,shortName,0 from CUPTI_ACTIVITY_KIND_KERNEL where start>=? and end<=? order by start',(lo,hi)).fetchall()
        per={}; busy=0; cs=ce=None
        for s,e,n,g in ks:
            k=names.get(n,str(n)); x=per.setdefault(k,[0,0]); x[0]+=1; x[1]+=e-s
            if ce is None: cs,ce=s,e
            elif s>ce: busy+=ce-cs; cs,ce=s,e
            else: ce=max(ce,e)
        if ce is not None: busy+=ce-cs
        mc=con.execute('select copyKind,count(*),sum(bytes),sum(end-start) from CUPTI_ACTIVITY_KIND_MEMCPY where start>=? and end<=? group by copyKind',(lo,hi)).fetchall()
        t=leg['timings']
        out[tag]=dict(wall_ns=hi-lo,busy_ns=busy,kernels=len(ks),tokens=t['predicted_n'],draft=t['draft_n'],acc=t['draft_n_accepted'],pred_ms=t['predicted_ms'],
                      memcpy={str(k):[n,bb,ns] for k,n,bb,ns in mc},per=per)
    con.close(); db.unlink(); res[d.name]=out
    print(d.name, {t:(round(v['wall_ns']/1e6),round(v['busy_ns']/1e6),v['kernels']) for t,v in out.items()}, flush=True)
json.dump(res,open(Path(sys.argv[1])/'CUT.json','w'))
