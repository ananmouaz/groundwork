#!/usr/bin/env python3
"""PreToolUse hook: no production edit before the record exists.

Reads the Claude Code hook payload on stdin and decides whether an Edit or
Write may proceed. Three rules keep it from becoming the thing people rip out
of their settings after a week:

1. It is inert until a project opts in. No `.groundwork/` directory in the
   project means the hook allows everything and says nothing.
2. It never blocks tests, markdown, or the record itself. Writing the record
   is how you satisfy it.
3. If anything about the hook itself fails — missing validator, unreadable
   payload, bad JSON — it allows the edit. A broken guard must not become a
   broken editor.

Modes, via GROUNDWORK_MODE:
    warn   (default) allow the edit, tell the agent what the record is missing
    block  deny the edit until the record validates
    off    do nothing

Other environment: GROUNDWORK_RECORD points at the record, GROUNDWORK_EXEMPT
adds colon-separated substrings that are never guarded, GROUNDWORK_VALIDATOR
points at validate_record.py.
"""

import json
import os
import re
import sys

GUARDED_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")

# Paths the guard never applies to. Editing these is either how you satisfy
# the guard, or is not production code in the first place.
EXEMPT_PATTERNS = (
    r"(^|/)\.groundwork/",
    r"(^|/)\.claude/",
    r"(^|/)(tests?|spec|specs|__tests__)/",
    r"(^|/)[^/]*[._-](test|spec)\.[^/]+$",
    r"(^|/)test_[^/]+$",
    r"\.(md|mdx|txt|rst|lock|snap)$",
    r"(^|/)\.[^/]+$",
)

MISSING = (
    "groundwork: no record for this change.\n"
    "Write %s before editing production code. Use the groundwork skill, or copy "
    "templates/RECORD.template.md. The record needs the facts you are relying on "
    "(each with the command that proved it), the blast radius with a verdict per "
    "row, and the invariants the change must not break."
)

INVALID = (
    "groundwork: the record %s does not validate yet.\n%s\n"
    "Fix those rows, then edit. `validate_record.py --rules` explains the codes."
)


def emit(decision, reason):
    """Speak the PreToolUse hook protocol, then stop."""
    output = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if decision == "deny":
        output["hookSpecificOutput"]["permissionDecision"] = "deny"
        output["hookSpecificOutput"]["permissionDecisionReason"] = reason
    else:
        output["hookSpecificOutput"]["additionalContext"] = reason
    sys.stdout.write(json.dumps(output))
    sys.exit(0)


def allow():
    sys.exit(0)


def find_validator(plugin_root, project):
    explicit = os.environ.get("GROUNDWORK_VALIDATOR")
    if explicit and os.path.exists(explicit):
        return explicit
    relative = os.path.join("skills", "groundwork", "scripts", "validate_record.py")
    roots = [
        plugin_root,
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.path.join(project, ".claude"),
        os.path.join(os.path.expanduser("~"), ".claude"),
    ]
    for root in roots:
        if not root:
            continue
        candidate = os.path.join(root, relative)
        if os.path.exists(candidate):
            return candidate
    return None


def load_validator(path):
    """Import validate_record.py from a path, on Python 3.4+."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("groundwork_validate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_exempt(path):
    normalized = path.replace(os.sep, "/")
    for pattern in EXEMPT_PATTERNS:
        if re.search(pattern, normalized):
            return True
    for extra in os.environ.get("GROUNDWORK_EXEMPT", "").split(":"):
        if extra and extra in normalized:
            return True
    return False


def record_path(project, validator):
    explicit = os.environ.get("GROUNDWORK_RECORD")
    if explicit:
        return explicit if os.path.isabs(explicit) else os.path.join(project, explicit)
    branch = validator.current_branch()
    if branch:
        candidate = os.path.join(project, ".groundwork", validator.slugify(branch) + ".md")
        if os.path.exists(candidate):
            return candidate
    return os.path.join(project, ".groundwork", "record.md")


def decide(payload, project, plugin_root):
    """-> (decision, reason). decision is 'allow' or 'deny'."""
    if os.environ.get("GROUNDWORK_MODE", "warn").lower() == "off":
        return "allow", None
    if payload.get("tool_name") not in GUARDED_TOOLS:
        return "allow", None

    target = payload.get("tool_input", {}).get("file_path") or ""
    if not target or is_exempt(target):
        return "allow", None

    # Opt-in: a project without a .groundwork directory is not using this.
    if not os.path.isdir(os.path.join(project, ".groundwork")):
        return "allow", None

    validator_path = find_validator(plugin_root, project)
    if not validator_path:
        return "allow", None
    validator = load_validator(validator_path)

    record = record_path(project, validator)
    blocking = os.environ.get("GROUNDWORK_MODE", "warn").lower() == "block"
    if not os.path.exists(record):
        return ("deny" if blocking else "allow"), MISSING % record

    with open(record) as handle:
        violations = validator.validate(handle.read())
    if not violations:
        return "allow", None

    listed = "\n".join("  %s:%s" % (os.path.basename(record), item)
                       for item in violations[:5])
    if len(violations) > 5:
        listed += "\n  ... and %d more" % (len(violations) - 5)
    return ("deny" if blocking else "allow"), INVALID % (record, listed)


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, IOError):
        allow()
    project = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    try:
        decision, reason = decide(payload, project, plugin_root)
    except Exception:
        # A guard that crashes must not stop the edit.
        allow()
    if reason is None:
        allow()
    emit(decision, reason)


if __name__ == "__main__":
    main()
