import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from checker.pohuy_check import check

SKILL_PATHS = ("SKILL.md", "references/slovar.md", "references/sceny.md")


def skill_digest(repo: Path) -> str:
    digest = hashlib.sha256()
    for rel in SKILL_PATHS:
        digest.update(rel.encode())
        digest.update(b"\0")
        digest.update((repo / rel).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def git(repo: Path, *args: str, input: bytes | None = None) -> str:
    out = subprocess.check_output(["git", "-C", str(repo), *args], input=input)
    return out.decode().strip()


def init_repo(repo: Path) -> None:
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "SKILL.md").write_bytes(b"skill\n")
    (repo / "references").mkdir()
    (repo / "references/slovar.md").write_bytes(b"slovar\n")
    (repo / "references/sceny.md").write_bytes(b"sceny\n")


def write_bundle(repo: Path, *, skill_sha: str, transcript: bytes, code_tree: str) -> None:
    session = b'{"kind":"session_start","skill":"pohuy","communication":"pohuy-only"}\n'
    if b'"skill":"other"' not in transcript and b'"communication":"pohuy-only"' not in transcript:
        transcript = session + transcript
    bundle = repo / ".pohuy-evidence" / "sub-1"
    bundle.mkdir(parents=True)
    (bundle / "transcript.ndjson").write_bytes(transcript)
    (bundle / "summary.md").write_text("asked, did, mapped\n", encoding="utf-8")
    (bundle / "skill.lock").write_text(skill_sha + "\n", encoding="utf-8")
    (bundle / "attestation.txt").write_text(
        "pohuy skill loaded\nagent committed\npohuy communication only\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": "pohuy.ai-evidence/v1",
        "covenant": "POHUY-COVENANT-1.0",
        "submission_id": "sub-1",
        "skill": {"name": "pohuy", "sha256": skill_sha},
        "transcript": {"sha256": hashlib.sha256(transcript).hexdigest()},
        "git": {"code_tree": code_tree},
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def commit(repo: Path) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "x")


class MissingEvidenceTest(unittest.TestCase):
    def test_missing_evidence_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            reasons = check(Path(raw))
        self.assertIn("missing evidence", reasons)


class BundleTest(unittest.TestCase):
    def test_skill_digest_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            init_repo(repo)
            git(repo, "add", "-A")
            tree = git(repo, "write-tree")
            write_bundle(repo, skill_sha="0" * 64, transcript=b'{"kind":"assistant_message"}\n', code_tree=tree)
            commit(repo)
            reasons = check(repo)
        self.assertIn("skill digest mismatch", reasons)

    def test_secret_in_transcript_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            init_repo(repo)
            git(repo, "add", "-A")
            tree = git(repo, "write-tree")
            write_bundle(
                repo,
                skill_sha=skill_digest(repo),
                transcript=b'{"kind":"assistant_message","content":"ghp_abcdefghijklmnopqrstuvwxyz0123456789"}\n',
                code_tree=tree,
            )
            commit(repo)
            reasons = check(repo)
        self.assertIn("secret in transcript", reasons)

    def test_communication_without_pohuy_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            init_repo(repo)
            git(repo, "add", "-A")
            tree = git(repo, "write-tree")
            write_bundle(
                repo,
                skill_sha=skill_digest(repo),
                transcript=b'{"kind":"human_message"}\n{"kind":"assistant_message","skill":"other"}\n',
                code_tree=tree,
            )
            commit(repo)
            self.assertIn("pohuy communication required", check(repo))


    def test_valid_bundle_passes_and_tamper_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            init_repo(repo)
            git(repo, "add", "-A")
            tree = git(repo, "write-tree")
            write_bundle(
                repo,
                skill_sha=skill_digest(repo),
                transcript=b'{"kind":"human_message"}\n{"kind":"assistant_message"}\n',
                code_tree=tree,
            )
            commit(repo)
            self.assertEqual(check(repo), [])
            lock = repo / ".pohuy-evidence" / "sub-1" / "skill.lock"
            lock.write_text("f" * 64 + "\n", encoding="utf-8")
            self.assertIn("skill digest mismatch", check(repo))


if __name__ == "__main__":
    unittest.main()
