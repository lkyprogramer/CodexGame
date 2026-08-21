import subprocess,tempfile
from pathlib import Path
sources=[str(p) for p in Path('src').rglob('*.java')]
with tempfile.TemporaryDirectory() as d:
 r=subprocess.run(['javac','-encoding','UTF-8','-d',d,*sources,'PublicTest.java'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(r.stdout,end='')
 if r.returncode:raise SystemExit(r.returncode)
 r=subprocess.run(['java','-ea','-cp',d,'PublicTest'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(r.stdout,end='');raise SystemExit(r.returncode)
