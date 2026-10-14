#!/usr/bin/env python3
"""Fail-closed checker for POHUY-COVENANT-1.0 evidence bundles."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

EVIDENCE = ".pohuy-evidence"
REQUIRED = (
    "manifest.json",
    "transcript.ndjson",
    "summary.md",
    "skill.lock",
    "attestation.txt",
)
SKILL_PATHS = (
    "SKILL.md",
    "references/slovar.md",
    "references/sceny.md",
)
SCHEMA = "pohuy.ai-evidence/v1"
COVENANT = "POHUY-COVENANT-1.0"
SECRET_MARKERS = ("ghp_", "github_pat_", "BEGIN PRIVATE KEY", "AKIA")


def skill_digest(repo: Path) -> str:
    digest = hashlib.sha256()
    for rel in SKILL_PATHS:
        digest.update(rel.encode())
        digest.update(b"\0")
        path = repo / rel
        digest.update(path.read_bytes() if path.is_file() else b"")
        digest.update(b"\0")
    return digest.hexdigest()


def code_tree(repo: Path) -> str | None:
    index = tempfile.NamedTemporaryFile(prefix="pohuy-index-", delete=False)
    index.close()
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = index.name
    try:
        subprocess.check_call(
            ["git", "-C", str(repo), "read-tree", "HEAD"],
            env=env,
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_call(
            [
                "git",
                "-C",
                str(repo),
                "rm",
                "-r",
                "--cached",
                "--ignore-unmatch",
                "--quiet",
                EVIDENCE,
            ],
            env=env,
            stderr=subprocess.DEVNULL,
        )
        out = subprocess.check_output(
            ["git", "-C", str(repo), "write-tree"],
            env=env,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    finally:
        os.unlink(index.name)
    return out.decode().strip()


def check(repo) -> list[str]:
    repo = Path(repo)
    evidence = repo / EVIDENCE
    bundles = sorted(p for p in evidence.iterdir() if p.is_dir()) if evidence.is_dir() else []
    if not bundles:
        return ["missing evidence"]
    reasons: list[str] = []
    expected_skill = skill_digest(repo)
    expected_tree = code_tree(repo)
    for bundle in bundles:
        reasons.extend(_check_bundle(bundle, expected_skill, expected_tree))
    return reasons


def _check_bundle(bundle: Path, expected_skill: str, expected_tree: str | None) -> list[str]:
    reasons: list[str] = []
    sid = bundle.name
    missing = [name for name in REQUIRED if not (bundle / name).is_file()]
    if missing:
        return [f"{sid}: missing {name}" for name in missing]

    transcript = (bundle / "transcript.ndjson").read_bytes()
    if any(marker.encode() in transcript for marker in SECRET_MARKERS):
        reasons.append("secret in transcript")

    try:
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return reasons + [f"{sid}: manifest is not json"]

    if manifest.get("schema") != SCHEMA:
        reasons.append(f"{sid}: schema mismatch")
    if manifest.get("covenant") != COVENANT:
        reasons.append(f"{sid}: covenant mismatch")
    skill = manifest.get("skill") or {}
    if skill.get("name") != "pohuy":
        reasons.append(f"{sid}: skill name mismatch")

    lock_lines = (bundle / "skill.lock").read_text(encoding="utf-8").splitlines()
    lock_sha = lock_lines[0].strip() if lock_lines else ""
    if lock_sha != expected_skill or skill.get("sha256") != expected_skill:
        reasons.append("skill digest mismatch")

    recorded_transcript = (manifest.get("transcript") or {}).get("sha256")
    if recorded_transcript != hashlib.sha256(transcript).hexdigest():
        reasons.append(f"{sid}: transcript digest mismatch")

    recorded_tree = (manifest.get("git") or {}).get("code_tree")
    if expected_tree is None or recorded_tree != expected_tree:
        reasons.append(f"{sid}: code tree mismatch")

    attestation = (bundle / "attestation.txt").read_text(encoding="utf-8")
    if "pohuy skill loaded" not in attestation or "agent committed" not in attestation:
        reasons.append(f"{sid}: attestation incomplete")
    return reasons


def main() -> int:
    reasons = check(Path.cwd())
    if reasons:
        for reason in reasons:
            print(reason, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
