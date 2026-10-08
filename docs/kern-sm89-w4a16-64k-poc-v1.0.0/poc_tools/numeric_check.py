"""Compare captured arrays at IDENTICAL teacher-forced inputs, not diverged generations.
Thresholds are engineering gates for the same quantized target, not BF16-model accuracy claims.
"""
import argparse,json,sys,math
from pathlib import Path
import numpy as np

def compare(a,b,rtol=0.002,atol=0.002):
    if not all(isinstance(x,(int,float)) and math.isfinite(x) and x>=0 for x in (rtol,atol)):
        raise ValueError('tolerances must be finite and nonnegative')
    if a.size==0 or b.size==0:return {'status':'FAIL','reason':'empty arrays provide no numerical evidence'}
    if a.shape!=b.shape:return {'status':'FAIL','reason':'shape mismatch'}
    if not np.isfinite(a).all() or not np.isfinite(b).all():return {'status':'FAIL','reason':'NaN/Inf'}
    aa=a.astype(np.float64);bb=b.astype(np.float64);err=np.abs(aa-bb)
    denom=max(float(np.sqrt(np.mean(aa*aa))),1e-12)
    rrmse=float(np.sqrt(np.mean(err*err))/denom)
    max_abs=float(err.max(initial=0));within=bool(np.all(err<=atol+rtol*np.abs(aa)))
    return {'status':'PASS' if within else 'FAIL','bit_equal':bool(a.dtype==b.dtype and a.tobytes()==b.tobytes()),'max_abs':max_abs,'rrmse':rrmse,'rtol':rtol,'atol':atol}

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--candidate',required=True);p.add_argument('--out',required=True);p.add_argument('--exact',action='store_true');p.add_argument('--rtol',type=float,default=0.002);p.add_argument('--atol',type=float,default=0.002);a=p.parse_args()
    # allow_pickle=False is mandatory; neither model nor test evidence may inject Python objects.
    results={}
    with np.load(a.reference,allow_pickle=False) as ref,np.load(a.candidate,allow_pickle=False) as cand:
        if not ref.files:raise SystemExit('FAIL: empty NPZ provides no evidence')
        if set(ref.files)!=set(cand.files):raise SystemExit('FAIL: array keys differ')
        for key in ref.files:
            results[key]=compare(ref[key],cand[key],a.rtol,a.atol)
            if a.exact and not results[key].get('bit_equal'):results[key]['status']='FAIL'
    out={'status':'PASS' if all(r['status']=='PASS' for r in results.values()) else 'FAIL','arrays':results,'contract':'same input ids, weight payload and schedule contract required; compare metadata separately'}
    Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps(out));return 0 if out['status']=='PASS' else 2
if __name__=='__main__':sys.exit(main())
