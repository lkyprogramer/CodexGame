import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gather_make_kernel", ROOT / "tools/gather_probe/make_kernel.py")
gather = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gather)


def oracle_source():
    return """static inline float hsum_float_8(const __m256 x) {
    return exact_old_reduction(x);
}
void ggml_vec_dot_iq3_s_q8_K(int n, float* s, const void* vx, const void* vy) {
    const block_iq3_s * x = vx;
    const block_q8_K * y = vy;
#if defined(__AVX2__)
""" + gather.OLD_LOOKUP + """
            const __m256i p1 = _mm256_madd_epi16(dot1, _mm256_set1_epi16(2*ls1+1));
            const __m256i p2 = _mm256_madd_epi16(dot2, _mm256_set1_epi16(2*ls2+1));
            sumi1 = _mm256_add_epi32(sumi1, p1);
            sumi2 = _mm256_add_epi32(sumi2, p2);
    accumf = _mm256_fmadd_ps(scale, values, accumf);
    *s = hsum_float_8(accumf);
#elif defined(__AVX__)
    old_other_branch();
#endif
}
"""


class GatherProbeGeneratorTests(unittest.TestCase):
    def tree(self, folder):
        root = Path(folder)
        tree, ggml = root / "tree", root / "ggml"
        cpu = tree / "src/kernels/cpu"
        cpu.mkdir(parents=True)
        (cpu / "native_expert.cpp").write_text(
            '#include "lab_gu_profile.hpp"\n'
            'void unchanged() {\n'
            '    const int mt_min = native_gu_mt_min(f.gu_type);   // #152\n'
            '}\n')
        (tree / "CMakeLists.txt").write_text("# original build\n")
        quants = ggml / "ggml/src/ggml-cpu/arch/x86/quants.c"
        quants.parent.mkdir(parents=True)
        quants.write_text(oracle_source())
        return tree, ggml, quants

    def test_only_lookup_and_cpp_boundary_adaptations_change_oracle_body(self):
        oracle, body, reduction = gather.oracle_parts(oracle_source())
        restored = body.replace(gather.NEW_LOOKUP, gather.OLD_LOOKUP)
        restored = restored.replace("x = reinterpret_cast<const block_iq3_s*>(vx);", "x = vx;")
        restored = restored.replace("y = reinterpret_cast<const block_q8_K*>(vy);", "y = vy;")
        restored = restored.replace("    return hsum_float_8(accumf);", "    *s = hsum_float_8(accumf);")
        expected = oracle[oracle.index("    const block_iq3_s"):].replace("#if defined(__AVX2__)", "")
        self.assertEqual(restored, expected)
        self.assertIn("exact_old_reduction(x)", reduction)
        self.assertIn("_mm256_madd_epi16", body)
        self.assertIn("_mm256_fmadd_ps", body)
        self.assertNotIn("_mm256_dpwssd", body)

    def test_applies_default_off_single_format_dispatch_and_replay_harness(self):
        with tempfile.TemporaryDirectory() as folder:
            tree, ggml, _ = self.tree(folder)
            receipt = gather.apply(tree, ggml)
            self.assertEqual(len(receipt["files"]), 7)
            cpu = tree / "src/kernels/cpu"
            native = (cpu / "native_expert.cpp").read_text()
            self.assertIn("f.gu_type==21 && nt==1 && !f.tail_off", native)
            dispatch = (cpu / "lab_gu_gather_dispatch.cpp").read_text()
            self.assertIn('std::getenv("STRATA_LAB_GU_GATHER")', dispatch)
            self.assertIn("return cpu_avx2_ok();", dispatch)
            self.assertNotIn("cpu_avx512_ok", dispatch)
            harness = (cpu / "lab_gu_gather_probe.cpp").read_text()
            self.assertIn("lookup_parity();", harness)
            self.assertIn("i<512?(i+j)%512", harness)
            self.assertIn("const uint32_t* grid=lab_gu_grid21()", harness)
            self.assertIn("{0,511,0,511,511,0,511,0}", harness)
            self.assertIn("real-pool-output", harness)
            self.assertIn("CANDIDATE_NOT_EXECUTED", harness)
            self.assertNotIn("integer_vectors", harness)
            self.assertNotIn("lab_gu_vnni", harness)

    def test_repeated_application_refuses_without_changing_any_file(self):
        with tempfile.TemporaryDirectory() as folder:
            tree, ggml, _ = self.tree(folder)
            gather.apply(tree, ggml)
            before = {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()}
            with self.assertRaises(ValueError):
                gather.apply(tree, ggml)
            self.assertEqual(before, {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()})

    def test_missing_native_anchor_refuses_before_any_tree_write(self):
        with tempfile.TemporaryDirectory() as folder:
            tree, ggml, _ = self.tree(folder)
            native = tree / "src/kernels/cpu/native_expert.cpp"
            native.write_text("// unsupported source\n")
            before = {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "GATHER_ANCHOR_COUNT"):
                gather.apply(tree, ggml)
            self.assertEqual(before, {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()})

    def test_changed_or_ambiguous_oracle_is_not_silently_accepted(self):
        for source in [oracle_source().replace("idx.index[7]", "idx.index[6]"),
                       oracle_source() + oracle_source()]:
            with self.assertRaises(ValueError):
                gather.oracle_parts(source)

    def test_existing_output_refuses_before_native_or_build_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            tree, ggml, _ = self.tree(folder)
            (tree / "src/kernels/cpu/lab_gu_gather.hpp").write_text("user content\n")
            before = {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "GATHER_OUTPUT_ALREADY_EXISTS"):
                gather.apply(tree, ggml)
            self.assertEqual(before, {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()})

    def test_build_has_real_red_stub_and_avx2_only_kernel_flags(self):
        self.assertIn("LAB_GU_GATHER_RED_STUB", gather.CMAKE)
        self.assertIn("#ifdef LAB_GU_GATHER_RED_STUB", gather.kernel_source("", ""))
        self.assertIn("-mavx2;-mfma;-mf16c;-mno-avx512f", gather.CMAKE)
        self.assertNotIn("-mavx512", gather.CMAKE)
        self.assertNotIn("-mavxvnni", gather.CMAKE)
        self.assertIn("_mm256_i32gather_epi32", gather.kernel_source("", ""))


if __name__ == "__main__":
    unittest.main()
