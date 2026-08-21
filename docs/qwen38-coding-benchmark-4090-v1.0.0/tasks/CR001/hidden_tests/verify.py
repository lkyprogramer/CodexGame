from pathlib import Path
import json, sys

workspace = Path(sys.argv[1])
answer_path = Path(sys.argv[2]) if len(sys.argv) > 2 else workspace / "answer.json"
rubric = json.loads(Path(__file__).with_name("rubric.json").read_text(encoding="utf-8"))
try:
    answer = json.loads(answer_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(json.dumps({"passed": False, "tests_passed": 0, "tests_total": len(rubric["issues"]), "score": 0.0, "error": f"invalid JSON answer: {exc}"}))
    raise SystemExit(1)
text = json.dumps(answer, ensure_ascii=False).lower()
matched = []
critical_missing = []
for issue in rubric["issues"]:
    ok = all(any(term.lower() in text for term in group) for group in issue["term_groups"])
    if ok:
        matched.append(issue["key"])
    elif issue.get("required", False):
        critical_missing.append(issue["key"])
total = len(rubric["issues"])
passed_count = len(matched)
threshold = float(rubric.get("pass_threshold", 0.8))
score = passed_count / total if total else 0.0
passed = score >= threshold and not critical_missing
print(json.dumps({"passed": passed, "tests_passed": passed_count, "tests_total": total, "score": score, "matched": matched, "critical_missing": critical_missing}, ensure_ascii=False))
raise SystemExit(0 if passed else 1)
