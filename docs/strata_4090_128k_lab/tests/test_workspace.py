import json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from lab import workspace
from lab.assets import snapshot,verify

def git(root,*args):
 return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.DEVNULL).strip()

class WorkspaceTests(unittest.TestCase):
 def test_prepare_uses_separate_clone_and_preserves_production(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);prod=root/'prod';prod.mkdir()
   git(prod,'init','-b','main');git(prod,'config','user.name','Test');git(prod,'config','user.email','test@localhost')
   (prod/'a.txt').write_text('base\n');git(prod,'add','.');git(prod,'commit','-m','base');base=git(prod,'rev-parse','HEAD')
   git(prod,'checkout','-b','feature');(prod/'a.txt').write_text('feature\n');git(prod,'commit','-am','feature');head=git(prod,'rev-parse','HEAD');git(prod,'checkout','main')
   cfg={'workspace':str(root/'lab'),'deployed_repo':str(prod),'min_free_disk_gib':0}
   locks={'baseline_sha':base,'repository_git':str(prod)}
   entry={'head_sha':head,'fork':'unused/unused'}
   before=(git(prod,'rev-parse','HEAD'),git(prod,'status','--porcelain'),(prod/'.git/config').read_bytes())
   with patch.object(workspace,'lock',return_value=locks),patch.object(workspace,'experiment',return_value=entry):
     result=workspace.prepare(cfg,2253)
   self.assertEqual(before,(git(prod,'rev-parse','HEAD'),git(prod,'status','--porcelain'),(prod/'.git/config').read_bytes()))
   self.assertTrue(Path(result['task']).exists());self.assertEqual(git(Path(result['candidate']),'rev-parse','HEAD'),base)
   self.assertEqual((prod/'a.txt').read_text(),'base\n')
 def test_assets_reject_changed_model(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'m.gguf').write_bytes(b'fixture');(p/'template').write_text('template');(p/'cfg.json').write_text('{}')
   c={'workspace':str(p/'work'),'deployed_repo':str(p),'deployed_config':str(p/'cfg.json'),'gguf':str(p/'m.gguf'),'template':str(p/'template')}
   snapshot(c);verify(c)
   (p/'m.gguf').write_bytes(b'fixture changed')
   with self.assertRaises(RuntimeError):verify(c)
