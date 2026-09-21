#!/usr/bin/env python3
"""Validate a groundwork record.

A record is a markdown file with six sections. This script checks the parts a
machine can check: that every fact carries a command, every blast-radius row
carries a verdict, every invariant carries a counterexample, and every plan
step cites the evidence it rests on.

It does not check whether any of that is *true*. That is the hunt's job, and
the hunt is a second agent reading this record against the repo.

Usage:
    validate_record.py [RECORD]            human-readable violations
    validate_record.py [RECORD] --json     machine-readable, for the hook
    validate_record.py [RECORD] --quiet    exit code only
    validate_record.py --rules             print the rule table

RECORD defaults to $GROUNDWORK_RECORD, then .groundwork/<branch>.md, then
.groundwork/record.md.

Exit codes: 0 clean, 1 violations found, 2 the record could not be read.
"""

import argparse
import json
import os
import re
import subprocess
import sys

SECTIONS = ["task", "facts", "blast radius", "invariants", "plan", "unknowns"]

PREFIX_OF = {
    "facts": "F",
    "blast radius": "B",
    "invariants": "I",
    "plan": "P",
    "unknowns": "U",
}

VERDICTS = ("SAFE", "UPDATE", "UNKNOWN")

# A hedge cannot be falsified, so it cannot be an invariant. This list is
# deliberately short: it catches the words a model reaches for when it has no
# evidence, not every soft word in English.
HEDGES = [
    "should", "shouldn't", "ideally", "probably", "generally", "usually",
    "typically", "might", "may", "properly", "proper", "appropriate",
    "appropriately", "reasonable", "reasonably", "robust", "clean", "cleanly",
    "correctly", "as needed", "if possible", "try to", "make sure",
]
HEDGE_RE = re.compile(r"\b(" + "|".join(re.escape(h) for h in HEDGES) + r")\b", re.I)

PLACEHOLDER_RE = re.compile(r"(\bTODO\b|\bTBD\b|\bFIXME\b|\?\?\?|<[a-z][a-z0-9 _/.-]*>)")
ROW_RE = re.compile(r"^[-*]\s+(.*\S)\s*$")
FIELD_RE = re.compile(r"\s+(?:—|--)\s+")
ID_RE = re.compile(r"^([FBIPU])([0-9]{1,3})$")
REF_RE = re.compile(r"\b([FBIU][0-9]{1,3})\b")
CODE_RE = re.compile(r"`([^`]+)`")
ARROW_RE = re.compile(r"(?:→|->)")
ENUM_RE = re.compile(r"^[-*]?\s*Enumerated by:\s*(.*\S)\s*$", re.I)
HEADING_RE = re.compile(r"^##\s+(.*\S)\s*$")

RULES = [
    ("GW001", "a required section is missing"),
    ("GW002", "the sections are out of order"),
    ("GW003", "a section has no content"),
    ("GW004", "a row has no id, or the fields are not separated by an em dash"),
    ("GW005", "two rows share an id"),
    ("GW006", "a fact carries no command in backticks"),
    ("GW007", "a fact carries no evidence after the arrow"),
    ("GW008", "the blast radius names no command that enumerated it"),
    ("GW009", "a blast-radius row carries no verdict (SAFE, UPDATE, UNKNOWN)"),
    ("GW010", "an UNKNOWN blast-radius row is not carried into Unknowns"),
    ("GW011", "an invariant names no counterexample (breaks if: ...)"),
    ("GW012", "an invariant is hedged, so nothing can falsify it"),
    ("GW013", "a plan step cites no fact, blast-radius row or invariant"),
    ("GW014", "a row refers to an id that does not exist"),
    ("GW015", "template placeholder text was left in"),
    ("GW016", "an unknown names no way to resolve it"),
]


class Violation(object):
    def __init__(self, line, code, subject, message):
        self.line = line
        self.code = code
        self.subject = subject
        self.message = message

    def as_dict(self):
        return {
            "line": self.line,
            "code": self.code,
            "subject": self.subject,
            "message": self.message,
        }

    def __str__(self):
        subject = (" " + self.subject) if self.subject else ""
        return "%d: %s%s — %s" % (self.line, self.code, subject, self.message)


def default_record_path():
    """$GROUNDWORK_RECORD, then the current branch's record, then record.md."""
    explicit = os.environ.get("GROUNDWORK_RECORD")
    if explicit:
        return explicit
    branch = current_branch()
    if branch:
        candidate = os.path.join(".groundwork", slugify(branch) + ".md")
        if os.path.exists(candidate):
            return candidate
    return os.path.join(".groundwork", "record.md")


def current_branch():
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    branch = out.decode("utf-8", "replace").strip()
    return None if branch in ("", "HEAD") else branch


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "record"


def parse_sections(lines):
    """-> list of (name, heading_line_number, [(line_number, text), ...])."""
    sections = []
    current = None
    for number, raw in enumerate(lines, start=1):
        heading = HEADING_RE.match(raw)
        if heading:
            current = (heading.group(1).strip().lower(), number, [])
            sections.append(current)
        elif current is not None:
            current[2].append((number, raw.rstrip()))
    return sections


def rows_of(body):
    """Top-level list rows only. An indented bullet is a note on its row."""
    found = []
    for number, text in body:
        match = ROW_RE.match(text)
        if match:
            found.append((number, match.group(1)))
    return found


def check_structure(sections, violations):
    present = [name for name, _, _ in sections]
    for name in SECTIONS:
        if name not in present:
            violations.append(Violation(1, "GW001", name, "section '## %s' is missing" % name))
    ordered = [name for name in present if name in SECTIONS]
    if ordered != [name for name in SECTIONS if name in ordered]:
        line = sections[0][1] if sections else 1
        violations.append(Violation(
            line, "GW002", "", "sections must run: " + ", ".join(SECTIONS)))


def check_placeholders(lines, violations):
    for number, raw in enumerate(lines, start=1):
        match = PLACEHOLDER_RE.search(raw)
        if match:
            violations.append(Violation(
                number, "GW015", "",
                "placeholder %r survived from the template" % match.group(1)))


def check_facts(body, violations):
    for number, text in rows_of(body):
        fields = FIELD_RE.split(text)
        ident = row_id(number, fields, "F", violations)
        if ident is None:
            continue
        if not CODE_RE.search(text):
            violations.append(Violation(
                number, "GW006", ident,
                "no command in backticks — a fact nobody can re-run is a belief"))
        after = ARROW_RE.split(text)
        if len(after) < 2 or not after[-1].strip():
            violations.append(Violation(
                number, "GW007", ident,
                "no evidence after the arrow — name the output line the command printed"))


def check_blast(body, violations, unknown_ids):
    enumerated = False
    for number, text in body:
        match = ENUM_RE.match(text.strip())
        if match and CODE_RE.search(match.group(1)):
            enumerated = True
    if not enumerated:
        line = body[0][0] if body else 1
        violations.append(Violation(
            line, "GW008", "",
            "no 'Enumerated by: `command`' line — say how the list was produced, "
            "or it is a list of what came to mind"))
    for number, text in rows_of(body):
        fields = FIELD_RE.split(text)
        ident = row_id(number, fields, "B", violations)
        if ident is None:
            continue
        verdict = [field for field in fields if field.strip() in VERDICTS]
        if not verdict:
            violations.append(Violation(
                number, "GW009", ident,
                "no verdict — every row needs one of: " + ", ".join(VERDICTS)))
        elif verdict[0].strip() == "UNKNOWN":
            unknown_ids.append((number, ident))


def check_invariants(body, violations):
    for number, text in rows_of(body):
        fields = FIELD_RE.split(text)
        ident = row_id(number, fields, "I", violations)
        if ident is None:
            continue
        lowered = text.lower()
        if "breaks if:" not in lowered:
            violations.append(Violation(
                number, "GW011", ident,
                "no 'breaks if:' — name the input or state that would make this false"))
        claim = FIELD_RE.split(text)
        claim_text = claim[1] if len(claim) > 1 else text
        hedge = HEDGE_RE.search(claim_text)
        if hedge:
            violations.append(Violation(
                number, "GW012", ident,
                "hedged on %r — an invariant nothing can falsify is not an invariant"
                % hedge.group(1)))


def check_plan(body, violations):
    for number, text in rows_of(body):
        fields = FIELD_RE.split(text)
        ident = row_id(number, fields, "P", violations)
        if ident is None:
            continue
        rest = text[len(fields[0]):]
        if not REF_RE.search(rest):
            violations.append(Violation(
                number, "GW013", ident,
                "cites nothing — name the facts, rows or invariants this edit rests on"))


def check_unknowns(body, violations, unknown_ids):
    text_body = " ".join(text for _, text in body)
    if re.match(r"^\s*none\s*$", text_body.strip(), re.I):
        if unknown_ids:
            number, ident = unknown_ids[0]
            violations.append(Violation(
                number, "GW010", ident,
                "verdict is UNKNOWN but Unknowns says none"))
        return
    rows = rows_of(body)
    for number, text in rows:
        fields = FIELD_RE.split(text)
        ident = row_id(number, fields, "U", violations)
        if ident is None:
            continue
        if "resolved by:" not in text.lower():
            violations.append(Violation(
                number, "GW016", ident,
                "no 'resolved by:' — name the command, file or person that answers it"))
    carried = " ".join(text for _, text in rows)
    for number, ident in unknown_ids:
        if not re.search(r"\b" + ident + r"\b", carried):
            violations.append(Violation(
                number, "GW010", ident,
                "verdict is UNKNOWN but no unknown carries %s" % ident))


def row_id(number, fields, prefix, violations):
    match = ID_RE.match(fields[0].strip()) if fields else None
    if not match or match.group(1) != prefix or len(fields) < 2:
        violations.append(Violation(
            number, "GW004", "",
            "expected '- %s1 — claim — ...' with em-dash separators" % prefix))
        return None
    return match.group(1) + match.group(2)


def validate(text):
    lines = text.splitlines()
    violations = []
    sections = parse_sections(lines)
    check_structure(sections, violations)
    check_placeholders(lines, violations)

    bodies = {}
    for name, heading_line, body in sections:
        if name not in SECTIONS:
            continue
        if name in bodies:
            continue
        bodies[name] = (heading_line, body)
        if not [1 for _, line in body if line.strip()]:
            violations.append(Violation(heading_line, "GW003", name, "section is empty"))

    seen = {}
    for name, prefix in PREFIX_OF.items():
        if name not in bodies:
            continue
        for number, text_row in rows_of(bodies[name][1]):
            fields = FIELD_RE.split(text_row)
            match = ID_RE.match(fields[0].strip()) if fields else None
            if not match:
                continue
            ident = match.group(1) + match.group(2)
            if ident in seen:
                violations.append(Violation(
                    number, "GW005", ident,
                    "id already used on line %d" % seen[ident]))
            else:
                seen[ident] = number

    unknown_ids = []
    if "facts" in bodies:
        check_facts(bodies["facts"][1], violations)
    if "blast radius" in bodies:
        check_blast(bodies["blast radius"][1], violations, unknown_ids)
    if "invariants" in bodies:
        check_invariants(bodies["invariants"][1], violations)
    if "plan" in bodies:
        check_plan(bodies["plan"][1], violations)
    if "unknowns" in bodies:
        check_unknowns(bodies["unknowns"][1], violations, unknown_ids)

    for name in SECTIONS:
        if name not in bodies:
            continue
        for number, text_row in rows_of(bodies[name][1]):
            own = ID_RE.match(FIELD_RE.split(text_row)[0].strip())
            for ref in REF_RE.findall(text_row):
                if own and ref == own.group(1) + own.group(2):
                    continue
                if ref not in seen:
                    violations.append(Violation(
                        number, "GW014", ref, "no row with this id exists"))

    violations.sort(key=lambda item: (item.line, item.code))
    return violations


def main(argv):
    parser = argparse.ArgumentParser(add_help=True, description=__doc__.split("\n")[0])
    parser.add_argument("record", nargs="?", default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--rules", action="store_true")
    args = parser.parse_args(argv)

    if args.rules:
        for code, description in RULES:
            print("%s  %s" % (code, description))
        return 0

    path = args.record or default_record_path()
    try:
        with open(path) as handle:
            text = handle.read()
    except IOError as error:
        if args.as_json:
            print(json.dumps({"ok": False, "path": path, "unreadable": str(error),
                              "violations": []}))
        elif not args.quiet:
            sys.stderr.write("validate_record.py: %s\n" % error)
        return 2

    violations = validate(text)
    if args.as_json:
        print(json.dumps({
            "ok": not violations,
            "path": path,
            "violations": [item.as_dict() for item in violations],
        }, indent=2))
    elif not args.quiet:
        for item in violations:
            print("%s:%s" % (path, item))
        if violations:
            print("\n%d violation(s). `validate_record.py --rules` explains the codes."
                  % len(violations))
        else:
            print("%s: clean — %d rows." % (path, len(re.findall(
                r"(?m)^[-*]\s+[FBIPU][0-9]", text))))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
