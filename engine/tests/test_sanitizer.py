"""Crash attribution on sanitizer logs (synthetic logs, shaped like real ASan output)."""

from proofgate.sandbox.sanitizer import parse_sanitizer

REPORTER_CRASH = """
=================================================================
==42==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x7ffd5 at pc 0x55 bp 0x7f sp 0x7f
WRITE of size 81 at 0x7ffd5 thread T0
    #0 0x7f3a in __interceptor_strcpy ../../../../src/libsanitizer/asan/asan_interceptors.cpp:440
    #1 0x55d1 in main /work/poc.c:12
    #2 0x7f2b in __libc_start_main ../csu/libc-start.c:308
SUMMARY: AddressSanitizer: stack-buffer-overflow /work/poc.c:12 in main
"""

PROJECT_CRASH = """
==7==ERROR: AddressSanitizer: heap-use-after-free on address 0x6020 at pc 0x55 bp 0x7f sp 0x7f
READ of size 8 at 0x6020 thread T0
    #0 0x55e0 in Curl_example_helper /build/curl/lib/example.c:210
    #1 0x55e1 in Curl_example_outer /build/curl/lib/example.c:388
    #2 0x55e2 in main /work/poc.c:30
SUMMARY: AddressSanitizer: heap-use-after-free /build/curl/lib/example.c:210 in Curl_example_helper
"""


def test_crash_in_reporter_code():
    report = parse_sanitizer(REPORTER_CRASH)
    assert report["kind"] == "stack-buffer-overflow"
    assert report["attribution"] == "reporter"
    assert report["top"]["file"] == "/work/poc.c"


def test_crash_in_project_code():
    report = parse_sanitizer(PROJECT_CRASH)
    assert report["attribution"] == "project"
    assert report["top"]["function"] == "Curl_example_helper"


def test_clean_log():
    assert parse_sanitizer("all good\nexit 0") is None
