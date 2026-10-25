"""FixBench: can a Nemotron agent fix real curl security bugs, verified by curl's own tests?

SWE-bench style, built from curl's public advisories: each instance is a CVE whose fix commit
added a regression test. The agent gets the advisory and the vulnerable checkout, reads code,
edits it, builds curl and runs the tests in a network-less sandbox, and iterates. It never sees
the maintainers' fix; grading uses the regression test plus nearby tests that must keep passing.
"""
