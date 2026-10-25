import io
from pathlib import Path
import tarfile
import tempfile
import unittest

from external_java_prepare import allowed_patch, extract_source


class PatchBoundaryTest(unittest.TestCase):
    def patch(self, path):
        return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
                "@@ -1 +1 @@\n-old\n+new\n")

    def test_only_production_java_is_accepted(self):
        self.assertTrue(allowed_patch(""))
        self.assertTrue(allowed_patch(self.patch("gson/src/main/java/com/google/gson/Gson.java")))
        self.assertTrue(allowed_patch(self.patch("gson/src/main/java/T.java").replace("+new", "+  \tnew")))
        for path in ["gson/src/test/java/Test.java", "pom.xml", "gson/src/main/java/../Test.java"]:
            self.assertFalse(allowed_patch(self.patch(path)), path)
        self.assertFalse(allowed_patch("not a patch"))

    def test_symlink_and_binary_rejected(self):
        self.assertFalse(allowed_patch("new mode 120000\n" + self.patch("gson/src/main/java/T.java")))
        self.assertFalse(allowed_patch("new file mode 120000\n" + self.patch("gson/src/main/java/T.java")))
        self.assertFalse(allowed_patch("GIT binary patch\n"))

    def test_archive_history_and_escape_rejected(self):
        for name in ["repo/.git/config", "repo/../outside"]:
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
                item = tarfile.TarInfo(name)
                item.size = 1
                archive.addfile(item, io.BytesIO(b"x"))
            with tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):
                    extract_source(buffer.getvalue(), Path(folder) / "base")


if __name__ == "__main__":
    unittest.main()
