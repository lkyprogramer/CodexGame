from pathlib import Path
import sys
from qcb.verifier_helpers import emit, run_python_unittest

workspace = Path(sys.argv[1])
test_file = Path(__file__).with_name("test_task.py")
passed, total, details = run_python_unittest(workspace, test_file)
emit(passed, total, details)
