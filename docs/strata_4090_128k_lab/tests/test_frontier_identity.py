import copy
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('frontier_identity',ROOT/'tools/frontier/identity.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.lock=json.loads((ROOT/'frontier/sources/LOCK.json').read_text())
        b=self.lock['research_baseline']
        self.receipt={'source':{'head':b['sha'],'port_files_match':True,'dirty_files':list(range(6)),'native_clean':True,'patch_match':True},'binary':{'sha256':b['binary_sha256_reported']},'dependencies':{'mismatches':[],'files':2},'assets':{'mismatches':[],'files':16,'full_hash_verified':True},'protection':{'count':13,'changed':[]},'service':{'ActiveState':'inactive','SubState':'dead'},'config':{'env':dict(b['mandatory_env']),'kv_resident':20480,'max_context':131072,'port':18089,'safety_tokens':4096,'request_overrides_present':False},'build':{'values':dict(b['mandatory_build'])}}
    def test_preparation_never_attests_runtime_or_deployment(self):
        r=module.validate_identity(self.receipt,self.lock)
        self.assertEqual(r['status'],'IDENTITY_LOCKED');self.assertEqual(r['runtime_activation'],'NOT_RUN');self.assertFalse(r['deployment_approved'])
    def test_wrong_source_port_native_or_hc_binary_rejected(self):
        for field,value in [('head','0'*40),('port_files_match',False),('native_clean',False),('patch_match',False),('dirty_files',[])]:
            d=copy.deepcopy(self.receipt);d['source'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):module.validate_identity(d,self.lock)
        d=copy.deepcopy(self.receipt);d['binary']['sha256']='9a6b441da4933d4de8c9ba88e0cdfc83d755c90ed99b184a1b0ae712f2fc00bb'
        with self.assertRaises(ValueError):module.validate_identity(d,self.lock)
    def test_missing_or_drifted_asset_dependency_and_protection_rejected(self):
        for section,key,value in [('assets','full_hash_verified',False),('assets','mismatches',['weight']),('assets','files',0),('dependencies','mismatches',['source']),('protection','count',12),('protection','changed',['production'])]:
            d=copy.deepcopy(self.receipt);d[section][key]=value
            with self.subTest(section=section,key=key),self.assertRaises(ValueError):module.validate_identity(d,self.lock)
    def test_presence_sensitive_profile_and_forbidden_zero_rejected(self):
        for key in ('STRATA_VERIFY_PROFILE','STRATA_STAGE_PIN','STRATA_ROUTE_RESIDENT'):
            d=copy.deepcopy(self.receipt);d['config']['env'][key]='0'
            with self.subTest(key=key),self.assertRaises(ValueError):module.validate_identity(d,self.lock)
    def test_explicit_service_env_conflict_rejected(self):
        for key,value in [('STRATA_REPLY_REUSE','0'),('STRATA_PRESERVE_THINKING','1')]:
            with self.subTest(key=key),self.assertRaises(ValueError):module.prepared_env({key:value})
        self.assertEqual(module.prepared_env({})['STRATA_PRESERVE_THINKING'],'0')

    def test_staged_native_change_is_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree=Path(tmp)
            def git(*args):return subprocess.check_output(['git',*args],cwd=tree,stderr=subprocess.DEVNULL)
            git('init','-q');(tree/'native.cpp').write_text('baseline')
            git('add','native.cpp');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture')
            (tree/'native.cpp').write_text('changed');git('add','native.cpp')
            names,patch=module.source_changes(tree)
            self.assertEqual(names,['native.cpp']);self.assertIn(b'changed',patch)

    def test_defaults_build_and_isolation_drift_rejected(self):
        for section,key,value in [('config','port',18343),('config','request_overrides_present',True),('config','safety_tokens',0)]:
            d=copy.deepcopy(self.receipt);d[section][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):module.validate_identity(d,self.lock)
        d=copy.deepcopy(self.receipt);d['config']['env']['STRATA_DEFAULTS']='main'
        with self.assertRaises(ValueError):module.validate_identity(d,self.lock)
        d=copy.deepcopy(self.receipt);d['build']['values']['CUDA_ARCHITECTURES']='120'
        with self.assertRaises(ValueError):module.validate_identity(d,self.lock)

if __name__=='__main__':unittest.main()
