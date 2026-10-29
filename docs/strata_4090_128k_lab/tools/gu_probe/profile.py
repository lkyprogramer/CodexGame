"""Decode the versioned GU profile; worker CPU time is distinct from phase wall time."""
import json
from pathlib import Path
import struct
import sys


def read_profile(path):
    raw=Path(path).read_bytes()
    if len(raw)%8 or len(raw)<64*8:raise ValueError('PROFILE_LENGTH')
    data=struct.unpack('<'+'Q'*(len(raw)//8),raw)
    if data[0]!=0x31454c49464f5250 or data[1]!=1 or data[3:5]!=(64,9):raise ValueError('PROFILE_HEADER')
    threads=data[2];phase=64;jobs=phase+64*4;work=jobs+64*9*2
    if threads<1 or threads>128 or data[8]!=len(raw) or len(data)!=work+threads*64*9*3:
        raise ValueError('PROFILE_GEOMETRY')
    formats={}
    for ty in range(64):
        p=data[phase+ty*4:phase+ty*4+4]
        if not p[0]:continue
        entry={'phases':p[0],'gu_phase_ns':p[1],'quant_phase_ns':p[2],'down_phase_ns':p[3],'nt':{}}
        for nt in range(1,9):
            j=data[jobs+(ty*9+nt)*2:jobs+(ty*9+nt)*2+2]
            if not j[0]:continue
            if j[1]!=j[0]*nt:raise ValueError('PROFILE_JOB_ENTRIES')
            sums=[0,0,0]
            for th in range(threads):
                i=work+((th*64+ty)*9+nt)*3
                for field in range(3):sums[field]+=data[i+field]
            entry['nt'][str(nt)]={'jobs':j[0],'entries':j[1],'row_calls':sums[0],
                                  'rows':sums[1],'worker_ns':sums[2]}
        formats[str(ty)]=entry
    if sum(v['phases'] for v in formats.values())!=data[5]:raise ValueError('PROFILE_PHASE_TOTAL')
    if sum(n['jobs'] for v in formats.values() for n in v['nt'].values())!=data[6]:raise ValueError('PROFILE_JOB_TOTAL')
    if sum(n['entries'] for v in formats.values() for n in v['nt'].values())!=data[7]:raise ValueError('PROFILE_ENTRY_TOTAL')
    candidates={int(k):v['nt'].get('1',{}).get('worker_ns',0) for k,v in formats.items()}
    selected=max(candidates,key=candidates.get) if candidates and max(candidates.values())>0 else None
    return {'version':1,'threads':threads,'phases':data[5],'jobs':data[6],'entries':data[7],
            'formats':formats,'selected_type':selected,
            'selection':'largest observed nt=1 GU worker CPU time; phase wall time is reported separately'}


if __name__=='__main__':print(json.dumps(read_profile(sys.argv[1]),indent=2))
