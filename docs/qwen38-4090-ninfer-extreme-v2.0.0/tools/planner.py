"""Cost-aware proposal selection reference. Inputs must be measured, not invented AL."""
import math

def choose_proposal(rows):
    if not rows: raise ValueError('no measured choices')
    scored=[]
    for r in rows:
        al=float(r['al']); base=float(r['round_ms']); extra=float(r['extra_ms'])
        if not all(map(math.isfinite,[al,base,extra])) or al<=0 or base<=0 or extra<0:
            raise ValueError('invalid measured cost')
        scored.append((al/(base+extra),r['name']))
    return max(scored, key=lambda x:x[0])[1]
