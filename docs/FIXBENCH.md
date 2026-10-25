# FixBench methodology

FixBench asks one question: **given a public security advisory and the vulnerable source tree, can an
open model produce a patch that curl's own test suite accepts?** It is built the way SWE-bench is
built, on curl's security history instead of GitHub issues.

## Instances

Source: curl's official advisory feed (`https://curl.se/docs/vuln.json`, OSV format). An advisory
becomes a candidate when:

1. its OSV `GIT` range names the commit that fixed it;
2. that fix commit is from 2023 or later (older trees predate the sandbox toolchain);
3. the fix commit adds or changes a test case under `tests/data/` (the regression test);
4. the fix touches at most 5 files under `lib/`, `src/`, `include/` (a focused fix, like one report).

29 advisories qualify. For each one, [`fixbench/dataset.py`](../engine/proofgate/fixbench/dataset.py)
records:

| Field | Meaning |
|---|---|
| `base` | the parent of the fix commit: the vulnerable code |
| `test_patch` | the fix commit's changes under `tests/` |
| `gold_patch` | everything else in the fix (docs and release notes excluded) |
| `fail_to_pass` | test cases the fix added or changed |
| `pass_to_pass` | up to 30 existing test cases sharing a `<keywords>` entry with them |
| `issue` | the advisory's summary and details: the only description the agent gets |

## Validation

An instance is kept only if, in the sandbox, each fail-to-pass test **fails on `base` + `test_patch`**
and **passes on `base` + `test_patch` + `gold_patch`**. Pass-to-pass tests are kept only if they pass in
both builds. This removes tests that need features the sandbox build lacks and fixes the sandbox cannot
observe.

Sandbox build: curl `--enable-debug --disable-shared` with OpenSSL, libssh2, nghttp2, libpsl,
libidn2 and NTLM; curl's own test servers, plus stunnel (HTTPS, FTPS) and sshd (SFTP, SCP). The
regression tests run under valgrind, as in curl's CI, so memory errors fail them.

**27 of 29 validate.** The two dropped instances are memory-safety bugs whose regression tests pass on
the vulnerable build even under valgrind: CVE-2026-92391 (`curl_mime_free` recursion) and
CVE-2024-7264 (ASN.1 date parser over-read). They are listed on the FixBench page with that reason.
AddressSanitizer would likely catch both, but GCC 12's ASan crash-loops on kernels with high mmap ASLR
entropy (Docker Desktop's WSL2 kernel among them), and we chose not to weaken ASLR on the host.

## The agent

[`fixbench/agent.py`](../engine/proofgate/fixbench/agent.py), on Nebius Token Factory with native
function calling:

- **Input:** the advisory (fenced as untrusted text), the names of the regression tests, the
  regression test's real failure on the vulnerable build (run once before the model starts), and a
  deterministic list of files where identifiers named in the advisory occur.
- **Tools:** `grep`, `ls`, `read`, `outline` and `function` (tree-sitter), `edit` (exact search and
  replace, `.c/.h` under `lib/`, `src/`, `include/` only), `run_tests`, `finish`.
- **Budget:** 40 replies, 4 test runs, a dollar cap per instance (default $0.60).
- **Guards:** repeated identical read-only calls are flagged; after 10 replies without an edit the
  agent is told to commit to a fix and test it; if it breaks a passing patch and cannot recover, its
  last green patch is kept.
- **Never seen:** the gold patch, the fix commit, or anything after `base` in history (the working tree
  is `base` plus the test files only).

## Grading

The final diff is built fresh and every fail-to-pass and pass-to-pass test is run. **Resolved** means
all of them pass. Also reported, per instance and per model: whether the first test run already passed,
whether the agent edited a file the maintainers edited ("localized"), whether it broke a nearby test,
curl's `checksrc.pl` warnings on the changed files ("style-clean"), cost, tokens and wall time.

## Threats to validity

- **Memorization.** Nemotron 3 Super's model card lists pre-training data to June 2025 and
  post-training data to February 2026. 20 of the 27 instances were fixed after February 2026, and the
  results are split at that date.
- **Test-guided repair.** The agent may run the regression test and read it, so in principle it could
  overfit to it. Mitigations: the nearby tests must keep passing, the system prompt forbids special-casing
  the test, and every patch is published next to the maintainers' patch for anyone to judge. This mirrors
  ProofGate's product flow, where a reproduced report comes with the reporter's reproduction.
- **Localization hints.** The deterministic starting points come from the advisory text alone, never
  from the fix.
- **Test adequacy.** A patch can pass curl's tests and still be incomplete. "Resolved" means "curl's own
  regression and nearby tests accept it", not "a maintainer would merge it". That decision stays human.
- **Sandbox differences.** The build is one configuration on one OS image. Instances whose behaviour
  depends on other TLS backends or platforms are out of scope.

## Reproduce

```
proofgate fixbench build                      # rebuild bench/fixbench.jsonl from curl's advisory feed
proofgate fixbench validate                   # Docker: base fails, gold passes
proofgate fixbench run --model super          # needs NEBIUS_API_KEY
proofgate fixbench table                      # README table
proofgate export-web --only fixbench          # data for the web page
```

CI reproduces one instance end to end (vulnerable build fails the regression test, curl's fix passes it)
on every push.
