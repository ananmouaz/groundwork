#!/usr/bin/env python3
"""Acquire and release the per-project groundwork hunt lock."""

import argparse
import datetime
import os
import subprocess
import sys
import time

MAX_AGE = 7200


def lock_path(project):
    return os.path.join(os.path.abspath(project), ".groundwork", "hunt.lock")


def age(path, now=None):
    return int(now if now is not None else time.time()) - int(os.stat(path).st_mtime)


def acquire(project, now=None):
    path = lock_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        lock_age = age(path, now)
        with open(path) as handle:
            detail = handle.read().strip() or "empty lock"
        if lock_age > MAX_AGE:
            sys.stderr.write(
                "groundwork: dead hunt left %s (%ds old): %s\n"
                "record the interrupted hunt, remove the lock explicitly, then retry; "
                "it was not taken over\n" % (path, lock_age, detail))
            return 3
        sys.stderr.write("groundwork: another hunt holds %s: %s\n" % (path, detail))
        return 1
    try:
        try:
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=project,
                stderr=subprocess.DEVNULL).decode().strip()
        except (OSError, subprocess.CalledProcessError):
            head = "unknown"
        started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        content = "head=%s started=%s\n" % (head, started)
        os.write(descriptor, content.encode("utf-8"))
    finally:
        os.close(descriptor)
    print(path)
    return 0


def release(project):
    path = lock_path(project)
    if not os.path.isfile(path):
        sys.stderr.write("groundwork: no hunt lock at %s\n" % path)
        return 1
    os.unlink(path)
    return 0


def main(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    take = subparsers.add_parser("acquire")
    take.add_argument("project")
    drop = subparsers.add_parser("release")
    drop.add_argument("project")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.error("choose acquire or release")
    if args.command == "acquire":
        return acquire(args.project)
    return release(args.project)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
