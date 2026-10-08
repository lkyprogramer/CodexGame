"""Finite-support analytical oracle for exact speculative rejection.
This validates probability algebra, NOT a GPU sampler or whole-engine quality.
"""
import math

def normalize(xs):
    xs=[float(x) for x in xs]
    if not xs or any(not math.isfinite(x) or x < 0 for x in xs) or sum(xs)<=0:
        raise ValueError('nonempty finite nonnegative mass required')
    s=math.fsum(xs)
    return [x/s for x in xs]

def deterministic_proposal(vocab, token):
    if vocab<1 or not 0<=token<vocab: raise ValueError('invalid token domain')
    return [float(i==token) for i in range(vocab)]

def residual(p,q):
    if len(p)!=len(q): raise ValueError('support mismatch')
    p,q=normalize(p),normalize(q)
    r=[max(a-b,0.) for a,b in zip(p,q)]
    return normalize(r) if math.fsum(r)>1e-15 else None

def corrected_marginal(p,q):
    if len(p)!=len(q): raise ValueError('support mismatch')
    p,q=normalize(p),normalize(q)
    accept=[min(a,b) for a,b in zip(p,q)]
    reject=max(0.,1.-math.fsum(accept))
    r=residual(p,q)
    if reject>1e-12 and r is None: raise ValueError('positive reject mass without residual')
    return [a+reject*(r[i] if r else 0.) for i,a in enumerate(accept)]
