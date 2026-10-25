from __future__ import annotations
import re, shutil, subprocess, tempfile, time, uuid
from pathlib import Path
from .core import ROOT, run
from .scoring import extract_java


def evaluate(text,task_id,image,output_dir):
    if not image: return {'pass':None,'reason':'JAVA_NOT_RUN: no preinstalled Docker JDK image configured'}
    try: code=extract_java(text)
    except ValueError as e: return {'pass':False,'reason':str(e)}
    # These tasks are pure algorithms; operating-system access is outside the task contract.
    forbidden=r'(?:java\.(?:io|nio|net|lang\.reflect)|ProcessBuilder|Runtime\s*\.|System\s*\.\s*(?:exit|setOut|setErr)|ClassLoader|\\u[0-9a-fA-F]{4})'
    if re.search(forbidden,code): return {'pass':False,'reason':'generated code violates pure-function evaluation contract'}
    if not re.fullmatch('[a-z0-9-]+',task_id): raise ValueError('Invalid Java task id')
    h=ROOT/'fixtures/java'/task_id/'Harness.java'
    if not h.exists(): raise ValueError('Missing fixed Java oracle')
    image_id=run(['docker','image','inspect',image,'--format','{{.Id}}'],timeout=30).stdout.strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',image_id): raise ValueError('Docker image must resolve to an immutable local image ID')
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    name='strata-lab-java-'+uuid.uuid4().hex[:12]
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='java-',dir=output_dir) as t:
        p=Path(t);p.chmod(0o755)
        (p/'Solution.java').write_text(code,encoding='utf-8');shutil.copyfile(h,p/'Harness.java')
        for q in p.iterdir():q.chmod(0o644)
        cmd=['docker','run','--name',name,'--rm','--pull=never','--network','none','--read-only','--cap-drop','ALL',
             '--security-opt','no-new-privileges','--memory','768m','--memory-swap','768m','--cpus','1','--pids-limit','64',
             '--user','65534:65534','--tmpfs','/tmp:rw,nosuid,size=128m','--mount',f'type=bind,src={p},dst=/work,readonly',
             image_id,'sh','-c','mkdir -p /tmp/classes && javac -J-Xmx256m -J-XX:ActiveProcessorCount=1 --release 8 -encoding UTF-8 -d /tmp/classes /work/Solution.java /work/Harness.java && java -Xmx256m -XX:ActiveProcessorCount=1 -cp /tmp/classes Harness']
        try:
            r=run(cmd,timeout=90,check=False)
            ok=r.returncode==0 and r.stdout.strip().endswith('ALL_OK')
            return {'pass':ok,'reason':'Java oracle passed' if ok else 'Java compile/test failed','output':r.stdout[-6000:],
                    'image_id':image_id,'evaluation_s':time.perf_counter()-started}
        except subprocess.TimeoutExpired:
            return {'pass':False,'reason':'JAVA_TIMEOUT','image_id':image_id}
        finally:
            # Exact generated container name only; never stop any other container.
            run(['docker','rm','-f',name],timeout=30,check=False)
