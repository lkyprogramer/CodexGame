from pathlib import Path
import sys
from qcb.verifier_helpers import emit, run_java_test

workspace = Path(sys.argv[1])
test_file = Path(__file__).with_name("TestMain.java")
passed, total, details = run_java_test(workspace, test_file)
emit(passed, total, details)
