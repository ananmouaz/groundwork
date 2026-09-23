#!/usr/bin/env python3
"""Rule-by-rule tests for the record validator.

Run: python3 tests/test_validate_record.py -v

Every test starts from the clean fixture and breaks exactly one thing, so a
failure names the rule that stopped working rather than "the record is bad".
"""

import importlib.util
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")

spec = importlib.util.spec_from_file_location(
    "validate_record",
    os.path.join(ROOT, "skills", "groundwork", "scripts", "validate_record.py"),
)
validate_record = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_record)


def read(name):
    with open(os.path.join(FIXTURES, name)) as handle:
        return handle.read()


def codes(text):
    return [item.code for item in validate_record.validate(text)]


class RecordShape(unittest.TestCase):
    def setUp(self):
        self.clean = read("clean.md")

    def swap(self, old, new):
        self.assertIn(old, self.clean, "fixture drifted: %r not found" % old)
        return self.clean.replace(old, new, 1)

    def assertFires(self, code, text):
        found = codes(text)
        self.assertIn(code, found, "expected %s, got %s" % (code, found or "nothing"))

    def assertOnly(self, code, text):
        """The mutation fires its own rule and nothing else."""
        self.assertEqual(set(codes(text)), {code})

    def test_clean_record_passes(self):
        self.assertEqual(codes(self.clean), [])

    def test_template_is_rejected_until_filled_in(self):
        with open(os.path.join(ROOT, "templates", "RECORD.template.md")) as handle:
            self.assertFires("GW015", handle.read())

    def test_missing_section(self):
        cut = self.clean[:self.clean.index("## Unknowns")]
        self.assertFires("GW001", cut)

    def test_sections_out_of_order(self):
        # Move the whole Invariants block ahead of Facts. Every section is still
        # present exactly once, so only the order can be what fires.
        start = self.clean.index("## Invariants")
        end = self.clean.index("## Plan")
        block = self.clean[start:end]
        without = self.clean[:start] + self.clean[end:]
        cut = without.index("## Facts")
        self.assertOnly("GW002", without[:cut] + block + without[cut:])

    def test_empty_section(self):
        emptied = self.swap(
            "A repeated `charge.refunded` delivery must return 200 without issuing a second refund.",
            "")
        self.assertOnly("GW003", emptied)

    def test_row_without_an_id(self):
        self.assertOnly("GW004", self.swap("- F3 — the webhook queue", "- the webhook queue"))

    def test_duplicate_id(self):
        self.assertOnly("GW005", self.swap("- F3 —", "- F1 —"))

    def test_fact_without_a_command(self):
        broken = self.swap(
            "- F3 — the webhook queue retries five times — `rg -n \"maxRetries\" infra/queue.ts` → `infra/queue.ts:17: maxRetries: 5`",
            "- F3 — the webhook queue retries five times — I read the config → five")
        self.assertOnly("GW006", broken)

    def test_fact_without_evidence(self):
        broken = self.swap(
            " — `rg -n \"maxRetries\" infra/queue.ts` → `infra/queue.ts:17: maxRetries: 5`",
            " — `rg -n \"maxRetries\" infra/queue.ts`")
        self.assertOnly("GW007", broken)

    def test_blast_radius_without_an_enumerating_command(self):
        broken = self.swap(
            "Enumerated by: `rg -n \"refundCharge\\(\" src/ tests/` → 6 hits",
            "I looked through the callers.")
        self.assertOnly("GW008", broken)

    def test_blast_row_without_a_verdict(self):
        self.assertOnly("GW009", self.swap(
            " — SAFE — the assertion still holds after the change", " — it is fine"))

    def test_unknown_verdict_not_carried_into_unknowns(self):
        broken = self.swap(
            "- U1 — whether the reconcile job in B3 reuses the provider event id — resolved by: `rg -n \"event_id\" src/jobs/reconcile.ts`",
            "none")
        self.assertOnly("GW010", broken)

    def test_unknown_verdict_carried_under_a_different_id_still_fires(self):
        broken = self.swap("whether the reconcile job in B3 reuses", "whether the job reuses")
        self.assertOnly("GW010", broken)

    def test_invariant_without_a_counterexample(self):
        broken = self.swap(
            " — breaks if: two deliveries commit in the same transaction window with no unique index",
            "")
        self.assertOnly("GW011", broken)

    def test_hedged_invariant(self):
        broken = self.swap(
            "- I2 — a duplicate delivery answers 200 and writes nothing",
            "- I2 — a duplicate delivery should answer 200 properly")
        self.assertOnly("GW012", broken)

    def test_a_hedge_in_a_fact_is_allowed(self):
        # Only invariants have to be falsifiable. Facts carry their own proof.
        self.assertEqual(codes(self.swap(
            "- F2 — every refund goes through", "- F2 — usually every refund goes through")), [])

    def test_plan_step_citing_nothing(self):
        self.assertOnly("GW013", self.swap(" — rests on B2", " — because it is needed"))

    def test_reference_to_an_id_that_does_not_exist(self):
        self.assertOnly("GW014", self.swap(" — rests on F1, I1", " — rests on F9, I1"))

    def test_placeholder_left_in(self):
        self.assertOnly("GW015", self.swap("src/jobs/reconcile.ts:52", "<path>"))

    def test_unknown_without_a_resolution(self):
        broken = self.swap(
            " — resolved by: `rg -n \"event_id\" src/jobs/reconcile.ts`",
            " — worth a look at some point")
        self.assertOnly("GW016", broken)

    def test_none_is_accepted_when_nothing_is_unknown(self):
        settled = self.clean.replace(" — UNKNOWN — unclear whether it reuses the provider event id",
                                     " — SAFE — it refunds through the same keyed path")
        settled = settled.replace(
            "- U1 — whether the reconcile job in B3 reuses the provider event id — resolved by: `rg -n \"event_id\" src/jobs/reconcile.ts`",
            "none")
        self.assertEqual(codes(settled), [])

    def test_an_indented_bullet_is_a_note_not_a_row(self):
        annotated = self.swap(
            "- F3 — the webhook queue retries five times",
            "  - the queue config is shared with the email worker\n- F3 — the webhook queue retries five times")
        self.assertEqual(codes(annotated), [])

    def test_double_hyphen_separates_fields_too(self):
        # Not every keyboard produces an em dash at 2am.
        self.assertEqual(codes(self.clean.replace(" — ", " -- ")), [])

    def test_four_full_hunts_are_rejected(self):
        extra = "\n- H2 — confirmation — gaps — 1\n- H3 — hunt — gaps — 1\n" \
                "- H4 — hunt — gaps — 1\n- H5 — hunt — gaps — 1\n"
        self.assertFires("GW019", self.clean + extra)

    def test_two_complete_verdicts_are_rejected(self):
        extra = "\n- H2 — confirmation — complete — 0\n"
        self.assertFires("GW020", self.clean + extra)

    def test_hunt_rounds_must_be_consecutive(self):
        self.assertFires("GW018", self.clean.replace("- H1", "- H2"))

    def test_round_one_must_be_a_hunt(self):
        broken = self.clean.replace(
            "- H1 — hunt — complete — 0",
            "- H1 — confirmation — gaps — 1")
        self.assertFires("GW018", broken)

    def test_closing_complete_round_must_be_a_hunt(self):
        broken = self.clean.replace(
            "- H1 — hunt — complete — 0",
            "- H1 — hunt — gaps — 1\n- H2 — confirmation — complete — 0")
        self.assertFires("GW018", broken)


class TreeState(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp(prefix="groundwork-tree-")
        subprocess.check_call(["git", "init", "-q"], cwd=self.project)
        subprocess.check_call(["git", "config", "user.email", "test@example.com"],
                              cwd=self.project)
        subprocess.check_call(["git", "config", "user.name", "Test"], cwd=self.project)
        with open(os.path.join(self.project, "tracked.txt"), "w") as handle:
            handle.write("base\n")
        subprocess.check_call(["git", "add", "tracked.txt"], cwd=self.project)
        subprocess.check_call(["git", "commit", "-qm", "base"], cwd=self.project)

    def tearDown(self):
        shutil.rmtree(self.project, ignore_errors=True)

    def record_for_tree(self):
        text = read("clean.md")
        digest = validate_record.tree_digest(self.project)
        return re.sub(r"(?m)^Tree: [0-9a-f]{40}$", "Tree: " + digest, text)

    def test_recorded_tree_passes(self):
        self.assertEqual(validate_record.validate(
            self.record_for_tree(), project=self.project), [])

    def test_tree_that_moved_mid_hunt_is_rejected(self):
        record = self.record_for_tree()
        with open(os.path.join(self.project, "tracked.txt"), "a") as handle:
            handle.write("moved\n")
        self.assertIn("GW017", [item.code for item in validate_record.validate(
            record, project=self.project)])


class ReportedOutput(unittest.TestCase):
    def test_violations_carry_the_line_they_are_on(self):
        text = read("clean.md").replace(" — rests on B2", " — because it is needed")
        violation = [item for item in validate_record.validate(text) if item.code == "GW013"][0]
        self.assertEqual(text.splitlines()[violation.line - 1].split(" — ")[0], "- P3")

    def test_every_rule_code_is_documented(self):
        # The rule table and the code must not drift apart: a violation the
        # table does not explain is a violation nobody can act on.
        with open(os.path.join(
                ROOT, "skills", "groundwork", "scripts", "validate_record.py")) as handle:
            source = handle.read()
        documented = set(code for code, _ in validate_record.RULES)
        emitted = set(re.findall(r'Violation\([^,]+,\s*"(GW[0-9]{3})"', source))
        self.assertTrue(emitted)
        self.assertEqual(emitted, documented)


if __name__ == "__main__":
    unittest.main()
