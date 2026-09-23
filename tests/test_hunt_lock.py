#!/usr/bin/env python3
"""Process-level tests for the hunt lock lifecycle."""

import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "skills", "groundwork", "scripts", "hunt_lock.py")


class HuntLock(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp(prefix="groundwork-lock-")
        subprocess.check_call(["git", "init", "-q"], cwd=self.project)

    def tearDown(self):
        shutil.rmtree(self.project, ignore_errors=True)

    def run_lock(self, *args):
        return subprocess.run(
            ["python3", SCRIPT] + list(args), cwd=self.project,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_hunt_acquires_and_releases(self):
        taken = self.run_lock("acquire", self.project)
        self.assertEqual(taken.returncode, 0, taken.stderr)
        released = self.run_lock("release", self.project)
        self.assertEqual(released.returncode, 0, released.stderr)
        self.assertFalse(os.path.exists(os.path.join(
            self.project, ".groundwork", "hunt.lock")))

    def test_dead_hunt_is_reported_and_not_silently_taken_over(self):
        self.assertEqual(self.run_lock("acquire", self.project).returncode, 0)
        path = os.path.join(self.project, ".groundwork", "hunt.lock")
        old = 1000
        os.utime(path, (old, old))
        retried = self.run_lock("acquire", self.project)
        self.assertEqual(retried.returncode, 3)
        self.assertIn("dead hunt", retried.stderr)
        with open(path) as handle:
            self.assertIn("started=", handle.read())


if __name__ == "__main__":
    unittest.main()
