#!/usr/bin/env python3
"""DCO check: the commit message must carry a Signed-off-by trailer
matching the commit author's email (same rule the CI DCO check applies)."""

import re
import shutil
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> int:
    sys.stderr.write(message)
    return 1


def author_email() -> str | None:
    """Return the commit author's email, "" if unset, or None on git failure
    (error message already written to stderr)."""
    git = shutil.which("git")
    if git is None:
        sys.stderr.write("ERROR: git not found on PATH.\n")
        return None
    # encoding="utf-8": text=True would use the locale codec (cp1252 on Windows) and crash on UTF-8 names.
    proc = subprocess.run(  # noqa: S603 -- constant argv, path resolved via shutil.which
        [git, "var", "GIT_AUTHOR_IDENT"], check=False, capture_output=True, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0:
        sys.stderr.write("ERROR: could not determine author identity (git var GIT_AUTHOR_IDENT failed).\n")
        return None
    match = re.search(r"<([^>]+)>", proc.stdout)
    return match.group(1) if match else ""


def main() -> int:
    if len(sys.argv) != 2:
        return fail("usage: check-dco.py <commit-msg-file>\n")
    # utf-8-sig strips a BOM (Windows editors); errors=replace survives other encodings.
    msg = Path(sys.argv[1]).read_text(encoding="utf-8-sig", errors="replace")

    # Merge commits are exempt, matching the CI DCO check.
    first_line = msg.splitlines()[0] if msg.splitlines() else ""
    if first_line.startswith("Merge "):
        return 0

    email = author_email()
    if email is None:
        return 1
    if not email:
        return fail("ERROR: could not determine author email; set user.name/user.email.\n")

    # \s*$ tolerates trailing whitespace / CRLF line endings (Windows).
    signed = re.compile(rf"^Signed-off-by: .* <{re.escape(email)}>\s*$", re.IGNORECASE | re.MULTILINE)
    if not signed.search(msg):
        return fail(
            f"ERROR: commit is missing a DCO sign-off for <{email}>.\n"
            "Run 'git commit --amend -s' for the last commit, or recommit with 'git commit -s'.\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
