import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pi_history',ROOT/'tools/frontier/pi_history.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class HistoryTests(unittest.TestCase):
    def base(self):
        return [{'type':'session','id':'SESSION'}, {'type':'message','id':'SYS','parentId':None,'message':{'role':'system','sections':{'rules':'Real rules'},'toolsAdded':[]}}, {'type':'message','id':'USER','parentId':'SYS','message':{'role':'user','content':[{'type':'text','text':'Actual request'}]}}, {'type':'message','id':'TARGET','parentId':'USER','message':{'role':'assistant','content':[{'type':'text','text':'Historical answer must not enter prompt'}]}}]
    def run_projection(self,rows):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'session.jsonl';p.write_text('\n'.join(json.dumps(x) for x in rows));return mod.project_session(p,'TARGET')
    def test_parent_chain_excludes_unrelated_branch_and_original_completion(self):
        rows=self.base();rows.insert(3,{'type':'message','id':'OTHER','parentId':'SYS','message':{'role':'user','content':[{'type':'text','text':'OTHER BRANCH'}]}})
        body,proof=self.run_projection(rows)
        self.assertEqual(body['messages'][-1]['content'],'Actual request');self.assertNotIn('OTHER',proof['branch_entry_ids']);self.assertFalse(proof['wire_capture']);self.assertEqual(body['tool_choice'],'none')
    def test_missing_parent_cycle_compaction_and_images_reject(self):
        variants=[]
        d=self.base();d[-1]['parentId']='MISSING';variants.append(d)
        d=self.base();d[2]['parentId']='USER';variants.append(d)
        d=self.base();d[2]['type']='compaction';variants.append(d)
        d=self.base();d[2]['message']['content'].append({'type':'image','data':'not exported'});variants.append(d)
        d=self.base();d[2]['message']={'role':'toolResult','toolCallId':'unknown','content':[]};variants.append(d)
        for index,d in enumerate(variants):
            with self.subTest(index=index),self.assertRaises(ValueError):self.run_projection(d)
    def test_unquoted_credentials_redacted(self):
        for text in ['apiKey=example_value_123','export ACCESS_TOKEN=example_value_123','password: example_value_123','https://user:example_value_123@example.invalid']:
            with self.subTest(text=text):
                clean=mod.sanitize(text,{})
                self.assertNotIn('example_value_123',clean)

    def test_secret_redaction_and_source_identity(self):
        rows=self.base();rows[2]['message']['content'][0]['text']='Bearer '+('a'*24)+' api_key="private_value_123" /Users/luo/repo'
        body,proof=self.run_projection(rows);text=body['messages'][-1]['content']
        self.assertNotIn('private_value_123',text);self.assertNotIn('a'*24,text);self.assertIn('/workspace/user',text);self.assertEqual(len(proof['source_file_sha256']),64)

if __name__=='__main__':unittest.main()
