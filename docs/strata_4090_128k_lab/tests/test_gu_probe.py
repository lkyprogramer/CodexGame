import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gu_probe_profile',ROOT/'tools/gu_probe/profile.py')
profile=importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
spec=importlib.util.spec_from_file_location('gu_probe_isa',ROOT/'tools/gu_probe/isa_audit.py')
isa=importlib.util.module_from_spec(spec);spec.loader.exec_module(isa)
spec=importlib.util.spec_from_file_location('gu_probe_analyze',ROOT/'tools/gu_probe/analyze.py')
analyze=importlib.util.module_from_spec(spec);spec.loader.exec_module(analyze)


class GuProbeProfileTests(unittest.TestCase):
    def fixture(self):
        nthreads=2;words=[0]*(64+64*4+64*9*2+nthreads*64*9*3)
        words[:9]=[0x31454c49464f5250,1,nthreads,64,9,1,2,3,8*len(words)]
        words[64+21*4:64+21*4+4]=[1,300,20,100]
        jobs=64+64*4
        words[jobs+(21*9+1)*2:jobs+(21*9+1)*2+2]=[1,1]
        words[jobs+(21*9+2)*2:jobs+(21*9+2)*2+2]=[1,2]
        work=jobs+64*9*2
        for thread in range(nthreads):
            for nt,ns in [(1,90),(2,200)]:
                i=work+((thread*64+21)*9+nt)*3;words[i:i+3]=[1,320,ns]
        return words

    def read(self,words):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'profile.bin';p.write_bytes(struct.pack('<'+'Q'*len(words),*words))
            return profile.read_profile(p)

    def test_miss_jobs_and_worker_time_are_separate_and_totals_close(self):
        data=self.read(self.fixture())
        self.assertEqual(data['jobs'],2);self.assertEqual(data['entries'],3)
        self.assertEqual(data['formats']['21']['nt']['1']['worker_ns'],180)
        self.assertEqual(data['formats']['21']['gu_phase_ns'],300)
        self.assertEqual(data['formats']['21']['nt']['2']['jobs'],1)
        self.assertEqual(data['selected_type'],21)

    def test_rejects_incomplete_or_inconsistent_capture(self):
        original=self.fixture()
        for index,value in [(0,0),(1,2),(6,3),(7,4),(8,1)]:
            words=original.copy();words[index]=value
            with self.assertRaises(ValueError):self.read(words)

    def test_selection_uses_nt1_worker_cost_not_model_layer_count(self):
        words=self.fixture();words[5]+=1;words[6]+=1;words[7]+=1
        words[64+17*4:64+17*4+4]=[1,100,10,40];jobs=64+64*4
        words[jobs+(17*9+1)*2:jobs+(17*9+1)*2+2]=[1,1]
        work=jobs+64*9*2;i=work+(17*9+1)*3;words[i:i+3]=[1,640,500]
        self.assertEqual(self.read(words)['selected_type'],17)

    def test_only_evex_256_nonsaturating_vnni_is_approved(self):
        self.assertEqual(isa.instruction('vpdpwssd','62','ymm0,ymm1,ymm2'),'AVX512VNNI+VL')
        for op,raw,args in [('vpdpwssd','c4','ymm0,ymm1,ymm2'),('vpdpwssds','62','ymm0,ymm1,ymm2'),
                            ('vpermb','62','ymm0,ymm1,ymm2'),('vpopcntd','62','ymm0,ymm1'),('vpdpwssd','62','zmm0,zmm1,zmm2')]:
            with self.assertRaises(ValueError):isa.instruction(op,raw,args)

    def test_baseline_probe_must_not_contain_evex_or_vex(self):
        for raw,op in [('62','vpbroadcastd'),('c5','vaddps'),('c4','vpdpwssd')]:
            with self.assertRaises(ValueError):isa.instruction(op,raw,'ymm0,ymm1',True)
        self.assertEqual(isa.instruction('cpuid','0f','',True),'baseline')

    def test_expansion_gate_requires_three_percent_point_and_positive_paired_ci(self):
        passed=analyze.paired_stats([.96]*6)
        self.assertTrue(passed['expansion_gate']);self.assertEqual(passed['bootstrap_samples'],46656)
        self.assertFalse(analyze.paired_stats([.970000001]*6)['expansion_gate'])
        wide=analyze.paired_stats([.87,.90,.92,1.01,1.02,1.03])
        self.assertGreater(wide['improvement_percent'],3);self.assertFalse(wide['expansion_gate'])

    def test_paired_statistics_reject_invalid_ratios(self):
        for ratios in [[1.0],[1.0,0.0],[1.0,float('nan')],[1.0,float('inf')]]:
            with self.assertRaises(ValueError):analyze.paired_stats(ratios)


if __name__=='__main__':unittest.main()
