"""Run physical database fixture tests and persist machine-readable evidence."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "benchmark_data" / "physical"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run BIRD-VN physical database fixture tests")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--all", action="store_true", help="Run the complete repository test suite")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifact_prefix = "all_test_results" if args.all else "fixture_test_results"
    xml_path = output / f"{artifact_prefix}.xml"
    basetemp = output / ".fixture_test_tmp"
    test_target = "tests" if args.all else "tests/test_benchmark_physical.py"
    command = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", f"--basetemp={basetemp}",
               f"--junitxml={xml_path}", "-q", test_target]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    cases = []
    if xml_path.exists():
        root = ET.parse(xml_path).getroot()
        for case in root.iter("testcase"):
            child = next(iter(case), None)
            cases.append({
                "name": case.attrib.get("name"),
                "classname": case.attrib.get("classname"),
                "duration_seconds": float(case.attrib.get("time", 0)),
                "status": "FAIL" if child is not None and child.tag in ("failure", "error") else
                          "SKIP" if child is not None and child.tag == "skipped" else "PASS",
                "detail": "" if child is None else (child.attrib.get("message", "") + "\n" + (child.text or ""))[:4000],
            })
    summary = {
        "suite": "all repository tests" if args.all else "BIRD-VN physical database fixtures",
        "command": command,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "process_exit_code": result.returncode,
        "status": "PASS" if result.returncode == 0 and cases and all(c["status"] in ("PASS", "SKIP") for c in cases) else "FAIL",
        "passed": sum(c["status"] == "PASS" for c in cases),
        "failed": sum(c["status"] == "FAIL" for c in cases),
        "skipped": sum(c["status"] == "SKIP" for c in cases),
        "tests": cases,
        "stdout": result.stdout[-8000:],
        "stderr": result.stderr[-8000:],
    }
    json_path = output / f"{artifact_prefix}.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Physical database fixture tests", "", f"- Suite: **{summary['suite']}**",
             f"- Status: **{summary['status']}**", f"- Passed: {summary['passed']}",
             f"- Failed: {summary['failed']}", f"- Skipped: {summary['skipped']}",
             f"- Python: {summary['python']}", f"- Finished UTC: {summary['finished_at_utc']}", "",
             "| Test | Status | Duration (s) |", "|---|---|---:|"]
    lines.extend(f"| {case['classname']}.{case['name']} | {case['status']} | {case['duration_seconds']:.3f} |" for case in cases)
    if summary["failed"]:
        for case in cases:
            if case["status"] == "FAIL":
                lines.extend(["", f"## Failure: {case['name']}", "", "```text", case["detail"], "```"])
    lines.extend(["", "Generated from pytest JUnit XML. Invalid fixtures are isolated temporary database copies; the benchmark snapshots remain unchanged."])
    (output / f"{artifact_prefix}.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Fixture tests {summary['status']}: {summary['passed']} passed, {summary['failed']} failed")
    print(f"Evidence: {json_path}")
    return 0 if summary["status"] == "PASS" else max(1, result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
