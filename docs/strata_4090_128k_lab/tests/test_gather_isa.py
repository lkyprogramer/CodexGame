import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('gather_isa', Path(__file__).parents[1]/'tools/gather_probe/isa_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class GatherIsaTests(unittest.TestCase):
    def test_gather_is_avx2_but_not_allowed_in_baseline(self):
        self.assertEqual(audit.classify('vpgatherdd','c4','ymm0,DWORD PTR [rax+ymm1*4],ymm2',False),'AVX2')
        with self.assertRaises(ValueError):
            audit.classify('vpgatherdd','c4','ymm0,DWORD PTR [rax+ymm1*4],ymm2',True)

    def test_vnni_evex_and_unlisted_ops_are_rejected(self):
        for mnemonic, raw, operands in [('vpdpwssd','c4','ymm0,ymm1,ymm2'),('vpaddd','62','ymm0,ymm1,ymm2'),('vpaddd','c4','zmm0,zmm1,zmm2'),('vpermb','c4','ymm0,ymm1,ymm2')]:
            with self.subTest(mnemonic=mnemonic,raw=raw,operands=operands), self.assertRaises(ValueError):
                audit.classify(mnemonic,raw,operands,False)


if __name__ == '__main__':
    unittest.main()
