"""Keep Discord running while knowledge always tracks a GitHub repo."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import aiohttp

from bot import engine

ROOT = Path(__file__).resolve().parents[1]
CODE_GLOBS = (
    "bot/bot.py",
    "bot/engine.py",
    "bot/updater.py",
    "bot/vision.py",
    "bot/vision_api.py",
    "bot/tactics.py",
    "bot/tactics_data.py",
    "bot/llm.py",
    "requirements.txt",
)


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "").strip().removeprefix("https://github.com/").removesuffix(".git")


def _branch() -> str:
    return os.getenv("GITHUB_BRANCH", "main").strip() or "main"


def _token() -> str:
    return os.getenv("GITHUB_TOKEN", "").strip() or os.getenv("GH_TOKEN", "").strip()


def _headers() -> dict:
    h = {"User-Agent": "COUNTERWATCH-bot", "Accept": "application/vnd.github+json"}
    tok = _token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def knowledge_url() -> str:
    repo = _repo()
    branch = _branch()
    path = os.getenv("GITHUB_KNOWLEDGE_PATH", "bot/knowledge.json").strip()
    if os.getenv("GITHUB_KNOWLEDGE_URL", "").strip():
        return os.getenv("GITHUB_KNOWLEDGE_URL", "").strip()
    if not repo:
        return ""
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"


def api_sha_url() -> str:
    repo = _repo()
    if not repo:
        return ""
    path = os.getenv("GITHUB_KNOWLEDGE_PATH", "bot/knowledge.json").strip()
    return f"https://api.github.com/repos/{repo}/commits?path={path}&sha={_branch()}&per_page=1"


async def _get_json(session: aiohttp.ClientSession, url: str):
    async with session.get(url, headers=_headers()) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


async def _get_text(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=_headers()) as resp:
        resp.raise_for_status()
        return await resp.text()


async def fetch_remote_knowledge() -> tuple[dict, str]:
    url = knowledge_url()
    if not url:
        return {}, ""
    async with aiohttp.ClientSession() as session:
        sha = ""
        api = api_sha_url()
        if api:
            try:
                commits = await _get_json(session, api)
                if isinstance(commits, list) and commits:
                    sha = commits[0].get("sha") or ""
            except Exception:
                sha = ""
        body = await _get_text(session, url)
        data = json.loads(body)
        if not sha:
            sha = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
        return data, sha


def git_pull() -> tuple[str, str]:
    if not (ROOT / ".git").exists():
        return "skipped", "git clone ではない"
    branch = _branch()
    try:
        subprocess.run(["git", "fetch", "origin", branch], cwd=ROOT, check=True, capture_output=True, text=True)
        before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        subprocess.run(["git", "pull", "--ff-only", "origin", branch], cwd=ROOT, check=True, capture_output=True, text=True)
        after = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if before == after:
            return "same", after
        return "updated", after
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or str(exc))[-400:]
        raise RuntimeError(err) from exc


def code_changed_since(sha_before: str) -> bool:
    if not (ROOT / ".git").exists() or not sha_before:
        return False
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", sha_before, "HEAD", "--", *CODE_GLOBS],
            cwd=ROOT,
            text=True,
        )
        return bool(out.strip())
    except subprocess.CalledProcessError:
        return False


def restart_process() -> None:
    os.execv(sys.executable, [sys.executable, "-m", "bot.bot"])


async def sync_from_github(pull_code: bool = False) -> str:
    """
    Refresh knowledge from GitHub. Discord gateway stays up.
    If GIT_AUTO_PULL is on and bot Python files changed, restart after pull.
    """
    notes = []
    pulled_sha = ""
    if pull_code and os.getenv("GIT_AUTO_PULL", "0").strip() not in ("0", "false", "no"):
        before = ""
        if (ROOT / ".git").exists():
            try:
                before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            except subprocess.CalledProcessError:
                before = ""
        status, pulled_sha = await asyncio.to_thread(git_pull)
        if status == "updated":
            notes.append(f"git pull → `{pulled_sha[:7]}`")
            engine.reload_from_disk()
            if code_changed_since(before):
                notes.append("コードが変わったのでプロセスを再起動する")
                await asyncio.sleep(1)
                restart_process()
        elif status == "same":
            notes.append("git は最新")
        else:
            notes.append(pulled_sha)

    data, sha = await fetch_remote_knowledge()
    if not data:
        if notes:
            return " / ".join(notes)
        return "GITHUB_REPO が未設定。ローカル knowledge.json を使う。"
    if sha and sha == engine.KNOWLEDGE_VERSION:
        notes.append("GitHub の知識データは最新")
        return " / ".join(notes)
    engine.apply_knowledge(data, version=sha)
    n = len(engine.HEROES)
    notes.append(f"知識データを GitHub から読み込み（{n} ヒーロー, `{sha[:7]}`）")
    return " / ".join(notes)
