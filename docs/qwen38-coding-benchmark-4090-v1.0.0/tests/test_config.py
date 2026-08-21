from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qcb.config import load_config


class ConfigTest(unittest.TestCase):
    def test_loads_normalized_example(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "config" / "normalized.example.toml")
        self.assertEqual(config.inference.lane, "normalized")
        self.assertFalse(config.inference.mtp_enabled)
        self.assertEqual(config.inference.context_size, 32768)
        self.assertEqual(config.endpoint.base_url, "http://127.0.0.1:8080/v1")

    def test_rejects_unknown_lane(self) -> None:
        content = """
[model]
id = "x"
[endpoint]
base_url = "http://localhost/v1"
model = "x"
[inference]
lane = "mixed"
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.toml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lane"):
                load_config(path)

    def test_rejects_normalized_mtp_and_reserved_extra_body(self) -> None:
        base = """
[model]
id = "x"
[endpoint]
base_url = "http://localhost/v1"
model = "x"
[inference]
lane = "normalized"
mtp_enabled = true
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.toml"
            path.write_text(base, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mtp_enabled"):
                load_config(path)

        conflict = """
[model]
id = "x"
[endpoint]
base_url = "http://localhost/v1"
model = "x"
[inference]
lane = "optimized"
extra_body = { temperature = 0.8 }
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.toml"
            path.write_text(conflict, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "extra_body"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
