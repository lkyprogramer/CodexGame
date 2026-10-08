"""Confirm the local base's relevant code, without reading weights or touching GPU."""
import argparse,hashlib,json,re
from pathlib import Path

PATHS=['src/CMakeLists.txt','src/ops/launcher/gqa_attention_decode.cu','src/ops/kernel/gqa_attention_decode_i8.cuh','src/ops/kernel/gqa_attention_prefill_i8.cuh','src/ops/kernel/e8_root_codec.cuh','src/targets/qwen3_8/impl/runtime/dflash_impl.h','src/targets/qwen3_8/impl/runtime/dflash_context_impl.h','src/targets/qwen3_8/export/ninfer/targets/qwen3_8/round_state.h','docs/maintainer/prefill-throughput-plan.md']

def audit(root):
    root=Path(root); files={}
    for rel in PATHS:
        p=root/rel
        files[rel]={'exists':p.is_file()}
        if p.is_file(): files[rel]['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    a=(root/PATHS[0]).read_text() if (root/PATHS[0]).exists() else ''
    b=(root/PATHS[1]).read_text() if (root/PATHS[1]).exists() else ''
    c=(root/PATHS[2]).read_text() if (root/PATHS[2]).exists() else ''
    return {'files':files,'small_t_compile_range':re.findall(r'foreach\(token RANGE (\d+) (\d+)\)',a),'small_t_predicate':re.findall(r'bool gqa_attention_uses_small_t[^\n]+',b),'half_coset_comment_present':'half-coset approximation' in c,'result':'READ_ONLY_SOURCE_FACTS_NOT_GPU_TEST'}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('root'); p.add_argument('--out',required=True); a=p.parse_args(); Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(audit(a.root),indent=2)+'\n')
