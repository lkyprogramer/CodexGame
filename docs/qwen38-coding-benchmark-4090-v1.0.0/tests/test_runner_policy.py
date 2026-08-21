from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qcb.config import EndpointConfig, InferenceConfig, ModelConfig, RunConfig
from qcb.runner import _safe_filename, run_suite
from qcb.util import append_jsonl


class RunnerPolicyTest(unittest.TestCase):
    def config(self, source: Path) -> RunConfig:
        return RunConfig(
            model=ModelConfig(id="org/model name", file="", sha256=""),
            endpoint=EndpointConfig(base_url="http://127.0.0.1:1/v1", model="local"),
            inference=InferenceConfig(
                lane="normalized",
                temperature=0.0,
                top_p=1.0,
                top_k=0,
                min_p=0.0,
                seed=42,
                max_tokens=128,
                context_size=4096,
                reasoning_effort="medium",
                mtp_enabled=False,
                tool_mode=True,
                max_tool_calls=4,
                max_retries=0,
                system_prompt_file="config/system-prompt.txt",
                extra_body={},
            ),
            source_path=source,
        )

    def test_model_id_is_safe_for_result_filename(self) -> None:
        self.assertEqual(_safe_filename("org/model name"), "org_model_name")

    def test_existing_result_requires_explicit_policy(self) -> None:
        benchmark_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            source = output / "config.toml"
            source.write_text("placeholder", encoding="utf-8")
            config = self.config(source)
            result = output / "org_model_name-normalized-smoke.jsonl"
            append_jsonl(
                result,
                {
                    "model": {"id": "org/model name"},
                    "lane": "normalized",
                    "suite": "smoke",
                    "seed": 42,
                    "task": {"id": "SF001"},
                },
            )
            with self.assertRaises(FileExistsError):
                run_suite(benchmark_root, [], config, "smoke", output, [42])
            resumed = run_suite(benchmark_root, [], config, "smoke", output, [42], resume=True)
            self.assertEqual(resumed, result)


if __name__ == "__main__":
    unittest.main()
