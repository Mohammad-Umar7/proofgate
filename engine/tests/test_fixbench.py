"""FixBench logic that needs neither Docker nor a model: test-log parsing, edits, grading."""

from proofgate.fixbench.agent import EDITABLE, _fuzzy_replace, _strip_numbers
from proofgate.fixbench.harness import TestRun, parse_runtests
from proofgate.fixbench.run import _files, metrics

LOG = """PG_BUILD_OK
test 1876 [verify no credentials present in effective URL after redirect]
s-p----em-- OK (1   out of 1  , remaining: 00:00, took 1.054s, duration: 00:01)
test 0002...[HTTP GET]

 2: protocol FAILED:
test 0003 SKIPPED: curl lacks crypto support
TESTFAIL: These test cases failed: 2
test 0004...[second runtests invocation]
 4: valgrind ERROR
TESTFAIL: These test cases failed: 4
PG_LOG_TAIL
"""


def test_parse_runtests_both_line_styles_and_both_invocations():
    status = parse_runtests(LOG, ["1876", "2", "3", "4", "5"])
    assert status == {"1876": "ok", "2": "fail", "3": "skip", "4": "fail", "5": "missing"}


def test_testrun_grading_requires_every_test():
    run = TestRun(True, {"1876": "ok", "2": "fail"})
    assert run.passed(["1876"])
    assert not run.passed(["1876", "2"])
    assert run.failing(["1876", "2", "9"]) == ["2", "9"]
    assert not TestRun(False).passed([])


def test_fuzzy_edit_keeps_original_indentation_of_unchanged_lines():
    text = "static bool f(int a,\n                   int b)\n{\n  return a;\n}\n"
    out = _fuzzy_replace(text, "static bool f(int a,\n  int b)\n{\n  return a;",
                         "static bool f(int a,\n  int b)\n{\n  /* new */\n  return a;")
    assert out == "static bool f(int a,\n                   int b)\n{\n  /* new */\n  return a;\n}\n"


def test_fuzzy_edit_refuses_ambiguous_matches():
    assert _fuzzy_replace("x;\ny;\nx;\n", "x;", "z;") is None


def test_line_number_gutter_is_stripped():
    assert _strip_numbers("  12  int x;\n  13  int y;\n") == "int x;\nint y;\n"
    assert _strip_numbers("int x = 12  ;\n") == "int x = 12  ;\n"


def test_only_source_files_are_editable():
    assert EDITABLE.match("lib/cookie.c") and EDITABLE.match("include/curl/curl.h")
    assert not EDITABLE.match("tests/data/test1629")
    assert not EDITABLE.match("lib/Makefile.inc")
    assert not EDITABLE.match("../etc/passwd")


def test_metrics_and_diff_files():
    diff = "--- a/lib/cookie.c\n+++ b/lib/cookie.c\n@@ -1 +1 @@\n-a\n+b\n"
    assert _files(diff) == {"lib/cookie.c"}
    row = dict(resolved=True, first_test_passed=True, localized=True, build_ok=True,
               f2p_passed=True, p2p_broken=[], cost_usd=0.1, turns=10, tests_run=2,
               seconds=100, published="2026-05-16")
    m = metrics([row, {**row, "resolved": False, "first_test_passed": False, "cost_usd": 0.3,
                       "published": "2024-10-09"}])
    assert m["resolved"] == 1 and m["n"] == 2
    assert m["cost_per_resolved_usd"] == 0.4
    assert m["post_cutoff"] == {"cutoff": "2026-03-01", "n": 1, "resolved": 1}
