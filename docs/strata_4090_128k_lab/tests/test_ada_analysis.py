from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/v027'))
import analyze_ada as a

class AdaAccountingTests(unittest.TestCase):
    def test_il_shape(self):
        s=a.decode_shape('native_mmvq_il_kernel<IlQ6K, (int)3, (int)2>',768)
        self.assertEqual((s['type_id'],s['ncols'],s['n_out_nominal']),(14,3,6144));self.assertNotIn('n_in',s)
        self.assertIsNone(a.decode_shape('unrelated',32))
    def test_multi_pair(self):
        self.assertEqual(a.decode_shape('native_mmvq_multi_kernel<Q4KTraits, (int)4, (int)4, (int)2, (bool)0, (bool)0>',3072)['n_out_nominal'],6144)
        self.assertIsNone(a.decode_shape('native_mmvq_multi_kernel<Q4KTraits, (int)4, (int)4, (int)1, (bool)0, (bool)1>',6144))
    def test_union_and_missing_correlation(self):
        cell={'type_id':14,'ncols':3,'n_out':6144,'base_rows':2,'new_rows':0,'classification':'changed_not_covered_by_old_override'}
        def k(name,start,end,x):return dict(name=name,start=start,end=end,gridX=x,gridY=1,gridZ=1,correlationId=1)
        out=a.accounting([k('native_mmvq_il_kernel<IlQ6K, (int)3, (int)2>',0,10,768),k('native_quantize_q8_1_kernel',5,15,1)],0,20,[cell],{})
        self.assertEqual(out['novel_plus_all_support_union_ns'],15);self.assertEqual(out['candidate_runtime_attribution'],{'missing_or_ambiguous':1})
    def test_unknown_is_in_conservative_union(self):
        def k(name,start,end):return dict(name=name,start=start,end=end,gridX=100,gridY=1,gridZ=1,correlationId=1)
        out=a.accounting([k('unknown_mmvq_kernel',0,10),k('native_q4_k_mmvq_kernel<(bool)1>',10,20)],0,30,[],{})
        self.assertEqual(out['unparsed_mmvq_union_ns'],10)
        self.assertEqual(out['novel_plus_support_plus_unknown_union_ns'],10)
    def test_rows_mismatch_is_explicit_and_conservative(self):
        cell={'type_id':14,'ncols':3,'n_out':6144,'base_rows':1,'new_rows':0,'classification':'changed_not_covered_by_old_override'}
        k=dict(name='native_mmvq_il_kernel<IlQ6K, (int)3, (int)2>',start=0,end=10,gridX=768,gridY=1,gridZ=1,correlationId=1)
        out=a.accounting([k],0,20,[cell],{})
        self.assertEqual(out['state'],'BASE_ROWS_MISMATCH')
        self.assertEqual(out['actual_rows_base_mismatch_union_ns'],10)
        self.assertFalse(out['kernel_groups'][0]['actual_rows_match_all_base_cells'])
        self.assertEqual(out['novel_plus_support_plus_unknown_union_ns'],10)
    def test_exact_non_ada_exclusions_and_qsa_names(self):
        names=['native_mmvq_multi_kernel<SmallTraits<IQ4NLBlock, (int)4>, (int)2>', 'native_small_mmvq_kernel<Q80Block, (int)8, (bool)1>', 'mmvq_multi_kernel<(int)21, (int)4, (bool)0, (bool)1>']
        for name in names:self.assertIsNotNone(a.mmvq_exclusion(name,None))
        self.assertIsNone(a.mmvq_exclusion('mmvq_multi_kernel<(int)23, (int)3>',None))
        self.assertIsNone(a.mmvq_exclusion('unknown_mmvq_kernel',None))
        self.assertEqual(a.qsa_family('block_scores_rows_kernel<(int)3>'),'QSA_BLOCK_SCORING')
        self.assertEqual(a.qsa_family('block_topk_reg_kernel<(int)33>'),'QSA_BLOCK_SELECTION')
        self.assertIsNone(a.qsa_family('mtp_select_kernel'))
    def test_missing_trace(self):self.assertEqual(a.analyze_trace('/missing.sqlite',{'all_cells':[]})['state'],'NO_TRACE')
    def test_markers_owner_integration(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'t.sqlite';c=sqlite3.connect(p)
            c.executescript('CREATE TABLE StringIds(id,value); CREATE TABLE PROCESSES(globalPid,pid,name); CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(start,end,deviceId,contextId,streamId,correlationId,globalPid,demangledName,gridX,gridY,gridZ); CREATE TABLE NVTX_EVENTS(start,end,text,textId);')
            c.execute('insert into StringIds values(1,"native_quantize_q8_1_kernel")');c.execute('insert into PROCESSES values(16777216,123,"strata")');c.execute('insert into CUPTI_ACTIVITY_KIND_KERNEL values(12,18,0,1,1,7,16777216,1,1,1,1)')
            c.executemany('insert into NVTX_EVENTS values(?,?,?,NULL)',[(0,30,'P11_REQUEST/x'),(10,None,'P11_FIRST/x'),(10,None,'P11_OUTPUT/x'),(20,None,'P11_OUTPUT/x')]);c.commit();c.close()
            out=a.analyze_trace(p,{'all_cells':[]},expected_pid=123);self.assertEqual(out['state'],'OBSERVED');self.assertEqual(out['requests'][0]['decode_observed']['kernel_union_ns'],6)
            self.assertEqual(a.analyze_trace(p,{'all_cells':[]},expected_pid=999)['state'],'UNATTRIBUTED')
            c=sqlite3.connect(p)
            c.execute('update StringIds set value=? where id=1',('native_mmvq_il_kernel<IlQ6K, (int)3, (int)2>',))
            c.execute('update CUPTI_ACTIVITY_KIND_KERNEL set gridX=768');c.commit();c.close()
            cell={'type_id':14,'ncols':3,'n_out':6144,'base_rows':1,'new_rows':0,'classification':'changed_not_covered_by_old_override'}
            mismatch=a.analyze_trace(p,{'all_cells':[cell]},expected_pid=123)
            self.assertEqual(mismatch['state'],'BASE_ROWS_MISMATCH')
            self.assertEqual(mismatch['requests'][0]['state'],'BASE_ROWS_MISMATCH')
if __name__=='__main__':unittest.main()
