#!/usr/bin/env python3
"""Tests for the pre-edit hook.

Run: python3 tests/test_hook.py -v

The hook is run the way Claude Code runs it: a real subprocess, one JSON
payload on stdin, one JSON decision on stdout. Nothing is imported, because
the contract under test is the process contract.
"""

import json
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HOOK = os.path.join(ROOT, "hooks", "require_record.py")
CLEAN = os.path.join(HERE, "fixtures", "clean.md")


def run_hook(project, tool="Edit", path="src/billing/refund.ts", env=None, raw=None):
    payload = json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": path},
        "cwd": project,
    })
    environment = dict(os.environ)
    environment.pop("GROUNDWORK_MODE", None)
    environment.pop("GROUNDWORK_RECORD", None)
    environment.pop("GROUNDWORK_EXEMPT", None)
    environment.update(env or {})
    process = subprocess.Popen(
        ["python3", HOOK], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=environment, cwd=project)
    out, err = process.communicate((raw if raw is not None else payload).encode())
    return process.returncode, out.decode().strip(), err.decode()


def decision_of(out):
    """-> ('allow'|'deny', reason). Silence means allow."""
    if not out:
        return "allow", ""
    body = json.loads(out)["hookSpecificOutput"]
    if body.get("permissionDecision") == "deny":
        return "deny", body["permissionDecisionReason"]
    return "allow", body.get("additionalContext", "")


class HookProject(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp(prefix="groundwork-test-")
        os.makedirs(os.path.join(self.project, "src", "billing"))
        with open(os.path.join(self.project, ".gitignore"), "w") as handle:
            handle.write(".groundwork/\n")
        subprocess.check_call(["git", "init", "-q"], cwd=self.project)
        subprocess.check_call(["git", "config", "user.email", "test@example.com"],
                              cwd=self.project)
        subprocess.check_call(["git", "config", "user.name", "Test"], cwd=self.project)
        subprocess.check_call(["git", "add", ".gitignore"], cwd=self.project)
        subprocess.check_call(["git", "commit", "-qm", "base"], cwd=self.project)

    def tearDown(self):
        shutil.rmtree(self.project, ignore_errors=True)

    def opt_in(self, record=None):
        os.makedirs(os.path.join(self.project, ".groundwork"), exist_ok=True)
        if record is not None:
            with open(os.path.join(self.project, ".groundwork", "record.md"), "w") as handle:
                handle.write(record)

    def clean_record(self):
        with open(CLEAN) as handle:
            return handle.read()


class InertUntilOptedIn(HookProject):
    def test_no_groundwork_directory_means_silence(self):
        code, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "block"})
        self.assertEqual((code, out), (0, ""))

    def test_mode_off_allows_everything(self):
        self.opt_in()
        code, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "off"})
        self.assertEqual((code, out), (0, ""))

    def test_other_tools_are_not_guarded(self):
        self.opt_in()
        code, out, _ = run_hook(self.project, tool="Bash", env={"GROUNDWORK_MODE": "block"})
        self.assertEqual((code, out), (0, ""))


class MissingRecord(HookProject):
    def test_warn_mode_allows_but_says_what_is_missing(self):
        self.opt_in()
        code, out, _ = run_hook(self.project)
        decision, reason = decision_of(out)
        self.assertEqual(code, 0)
        self.assertEqual(decision, "allow")
        self.assertIn("no record for this change", reason)
        self.assertIn(".groundwork/record.md", reason)

    def test_block_mode_denies(self):
        self.opt_in()
        _, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "block"})
        decision, reason = decision_of(out)
        self.assertEqual(decision, "deny")
        self.assertIn("no record", reason)


class RecordPresent(HookProject):
    def test_a_valid_record_opens_the_gate_silently(self):
        self.opt_in(self.clean_record())
        code, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "block"})
        self.assertEqual((code, out), (0, ""))

    def test_an_invalid_record_is_denied_with_its_codes(self):
        self.opt_in(self.clean_record().replace(" — rests on B2", " — because it is needed"))
        _, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "block"})
        decision, reason = decision_of(out)
        self.assertEqual(decision, "deny")
        self.assertIn("GW013", reason)
        self.assertIn("record.md", reason)

    def test_a_long_violation_list_is_truncated(self):
        # An empty record misses every section. The agent gets five lines
        # and a count, not a wall.
        self.opt_in("# groundwork — nothing\n")
        _, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "block"})
        _, reason = decision_of(out)
        listed = [line for line in reason.splitlines() if "GW001" in line]
        self.assertEqual(len(listed), 5)
        self.assertIn("and ", reason)

    def test_an_explicit_record_path_is_honoured(self):
        self.opt_in()
        elsewhere = os.path.join(self.project, "notes", "plan.md")
        os.makedirs(os.path.dirname(elsewhere))
        with open(elsewhere, "w") as handle:
            handle.write(self.clean_record())
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=self.project)
        digest = hashlib.sha1(status).hexdigest()
        with open(elsewhere) as handle:
            text = handle.read()
        with open(elsewhere, "w") as handle:
            handle.write(text.replace(
                "da39a3ee5e6b4b0d3255bfef95601890afd80709", digest))
        code, out, _ = run_hook(self.project, env={
            "GROUNDWORK_MODE": "block", "GROUNDWORK_RECORD": "notes/plan.md"})
        self.assertEqual((code, out), (0, ""))


class HuntLock(HookProject):
    def lock(self):
        self.opt_in(self.clean_record())
        path = os.path.join(self.project, ".groundwork", "hunt.lock")
        with open(path, "w") as handle:
            handle.write("round=2 kind=confirmation\n")
        return path

    def test_fresh_lock_denies_even_an_exempt_write_in_block_mode(self):
        self.lock()
        _, out, _ = run_hook(self.project, path="tests/new_test.py",
                             env={"GROUNDWORK_MODE": "block"})
        decision, reason = decision_of(out)
        self.assertEqual(decision, "deny")
        self.assertIn("frozen tree", reason)

    def test_fresh_lock_warns_in_warn_mode(self):
        self.lock()
        _, out, _ = run_hook(self.project)
        decision, reason = decision_of(out)
        self.assertEqual(decision, "allow")
        self.assertIn("frozen tree", reason)

    def test_stale_lock_does_not_block(self):
        path = self.lock()
        old = 1000
        os.utime(path, (old, old))
        _, out, _ = run_hook(self.project, env={
            "GROUNDWORK_MODE": "block", "GROUNDWORK_LOCK_NOW": "8201"})
        self.assertEqual(decision_of(out)[0], "allow")

    def test_lock_does_not_block_a_path_outside_the_project(self):
        self.lock()
        _, out, _ = run_hook(self.project, path=os.path.join(
            os.path.dirname(self.project), "outside.py"),
            env={"GROUNDWORK_MODE": "block"})
        self.assertEqual(decision_of(out)[0], "allow")


class ExemptPaths(HookProject):
    def guarded(self, path):
        self.opt_in()
        _, out, _ = run_hook(self.project, path=path, env={"GROUNDWORK_MODE": "block"})
        return decision_of(out)[0] == "deny"

    def test_production_code_is_guarded(self):
        self.assertTrue(self.guarded("src/billing/refund.ts"))

    def test_writing_the_record_is_never_blocked(self):
        self.assertFalse(self.guarded(".groundwork/record.md"))

    def test_tests_are_not_blocked(self):
        self.assertFalse(self.guarded("tests/billing/refund.test.ts"))
        self.assertFalse(self.guarded("src/billing/refund.test.ts"))
        self.assertFalse(self.guarded("api/test_refund.py"))

    def test_markdown_is_not_blocked(self):
        self.assertFalse(self.guarded("docs/refunds.md"))

    def test_dotfiles_are_not_blocked(self):
        self.assertFalse(self.guarded(".env.example"))

    def test_extra_exemptions_come_from_the_environment(self):
        self.opt_in()
        _, out, _ = run_hook(self.project, path="src/generated/schema.ts",
                             env={"GROUNDWORK_MODE": "block",
                                  "GROUNDWORK_EXEMPT": "src/generated/"})
        self.assertEqual(decision_of(out)[0], "allow")


class FailsOpen(HookProject):
    def test_a_payload_that_is_not_json_allows_the_edit(self):
        self.opt_in()
        code, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "block"},
                                raw="this is not json")
        self.assertEqual((code, out), (0, ""))

    def test_an_unreadable_record_allows_the_edit(self):
        self.opt_in()
        os.makedirs(os.path.join(self.project, ".groundwork", "record.md"))
        code, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "block"})
        self.assertEqual((code, out), (0, ""))

    def test_a_missing_validator_allows_the_edit(self):
        # Run a copy of the hook from outside the repo, so none of the four
        # lookup roots can find validate_record.py. A guard that cannot check
        # anything must not be a guard that blocks everything.
        self.opt_in()
        stray = os.path.join(self.project, "hooks")
        os.makedirs(stray)
        shutil.copy(HOOK, stray)
        payload = json.dumps({"tool_name": "Edit",
                              "tool_input": {"file_path": "src/billing/refund.ts"},
                              "cwd": self.project})
        environment = dict(os.environ)
        environment.update({"GROUNDWORK_MODE": "block", "HOME": self.project,
                            "CLAUDE_PLUGIN_ROOT": self.project})
        environment.pop("GROUNDWORK_VALIDATOR", None)
        process = subprocess.Popen(
            ["python3", os.path.join(stray, "require_record.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=environment, cwd=self.project)
        out, _ = process.communicate(payload.encode())
        self.assertEqual((process.returncode, out.decode().strip()), (0, ""))

    def test_a_payload_without_a_file_path_allows_the_edit(self):
        self.opt_in()
        payload = json.dumps({"tool_name": "Edit", "tool_input": {}, "cwd": self.project})
        code, out, _ = run_hook(self.project, env={"GROUNDWORK_MODE": "block"}, raw=payload)
        self.assertEqual((code, out), (0, ""))


if __name__ == "__main__":
    unittest.main()
