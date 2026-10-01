"""Where the tracker's data lives, and how it is written. Python 3 stdlib only.

The data is kept apart from the application code:

    <root>/
      Job Tracker App/   the app (this folder): server, pages, scripts
      Data/              data.json (jobs), contacts.json (people), backups/

The data folder is, in order:
  1. TRACKER_DATA_DIR, if set;
  2. <root>/Data, if it holds data.json;
  3. this app folder, if it still holds data.json (installs from before the
     Data folder existed keep working untouched);
  4. otherwise <root>/Data, created on first write.

Optional GitHub sync, for hosts whose disk is wiped on restart (e.g. Render's
free plan). Set TRACKER_GITHUB_TOKEN and TRACKER_GITHUB_REPO ("owner/name"),
and optionally TRACKER_GITHUB_BRANCH (default "main"). Then:
  - on start-up, and before serving a data file (at most every few seconds),
    the latest version is pulled from the repo;
  - every save is committed straight to the repo.
Files map to the repo by their path relative to <root>, so <root> must be the
repo root (e.g. Data/data.json). Without those variables nothing touches the
network.
"""
import base64
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)  # the job-hunt folder (repo root)
KEEP_BACKUPS = 20


def resolve_data_dir():
    env = os.environ.get("TRACKER_DATA_DIR", "").strip()
    if env:
        return os.path.abspath(os.path.expanduser(env))
    data = os.path.join(ROOT_DIR, "Data")
    if os.path.exists(os.path.join(data, "data.json")):
        return data
    if os.path.exists(os.path.join(APP_DIR, "data.json")):
        return APP_DIR  # legacy layout: data still inside the app folder
    return data


DATA_DIR = resolve_data_dir()
DATA_FILE = os.path.join(DATA_DIR, "data.json")
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


# ---- files ----------------------------------------------------------------
def read_bytes(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def read_json(path, default):
    raw = read_bytes(path)
    return default if raw is None else json.loads(raw.decode("utf-8"))


def file_revision(path):
    """SHA-256 hex of the file's bytes; "" if it's missing. A cheap
    optimistic-concurrency token: a writer passes back the revision it loaded,
    and a save is refused if the file has changed since."""
    raw = read_bytes(path)
    return "" if raw is None else hashlib.sha256(raw).hexdigest()


def atomic_write_bytes(path, data):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    basename = os.path.basename(path)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=basename + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def atomic_write(path, text):
    atomic_write_bytes(path, text.encode("utf-8"))


def rotate_backup(path, prefix):
    """Copy `path` to backups/<prefix>-<stamp>.json and keep the newest KEEP_BACKUPS per prefix."""
    if not os.path.exists(path):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"{prefix}-{stamp}.json")
    try:
        with open(path, "rb") as src, open(dest, "wb") as dst:
            dst.write(src.read())
    except OSError:
        return
    pattern = re.compile(re.escape(prefix) + r"-\d{8}-\d{6}\.json")
    backups = sorted(f for f in os.listdir(BACKUP_DIR) if pattern.fullmatch(f))
    for old in backups[:-KEEP_BACKUPS]:
        try:
            os.remove(os.path.join(BACKUP_DIR, old))
        except OSError:
            pass


# ---- GitHub sync ----------------------------------------------------------
class SyncConflict(Exception):
    """The repo copy changed since we last pulled it; the local copy now holds the repo's version."""


class SyncPending(Exception):
    """The save is on disk here but couldn't reach GitHub yet; it is retried on the next sync."""


def git_blob_sha(data):
    """The SHA git (and GitHub's contents API) uses to identify a file's bytes."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class GitHubSync:
    REFRESH_SECONDS = 10

    def __init__(self, token="", repo="", branch="main", api="https://api.github.com"):
        self.token, self.repo, self.branch = token, repo.strip("/"), branch or "main"
        self.api = api.rstrip("/")
        self.enabled = bool(token and repo)
        self.lock = threading.RLock()
        self.shas = {}     # repo path -> blob sha of the repo version our local copy matches
        self.checked = {}  # repo path -> monotonic time of the last remote check
        self.dirty = set() # repo paths saved locally but not yet pushed

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("TRACKER_GITHUB_TOKEN", ""),
                   os.environ.get("TRACKER_GITHUB_REPO", ""),
                   os.environ.get("TRACKER_GITHUB_BRANCH", "main"),
                   os.environ.get("TRACKER_GITHUB_API", "https://api.github.com"))

    @staticmethod
    def repo_path(path):
        return os.path.relpath(os.path.abspath(path), ROOT_DIR).replace(os.sep, "/")

    def _call(self, method, rel, body=None, params=None):
        """(status, json) for a contents-API call; raises OSError if GitHub can't be reached."""
        url = f"{self.api}/repos/{self.repo}/contents/{urllib.parse.quote(rel)}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "job-tracker",
        }, data=None if body is None else json.dumps(body).encode("utf-8"))
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read() or b"{}")
            except ValueError:
                payload = {}
            return e.code, payload

    def _remote(self, rel):
        """(sha, bytes) of the repo copy, or (None, None) if it isn't in the repo."""
        status, meta = self._call("GET", rel, params={"ref": self.branch})
        if status == 404:
            return None, None
        if status != 200 or not isinstance(meta, dict) or "sha" not in meta:
            raise OSError(f"GitHub GET {rel} returned {status}: {meta.get('message', '') if isinstance(meta, dict) else ''}")
        content = meta.get("content") or ""
        if not content and meta.get("size"):  # files over 1 MB: fetch the blob instead
            req = urllib.request.Request(f"{self.api}/repos/{self.repo}/git/blobs/{meta['sha']}", headers={
                "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                "User-Agent": "job-tracker"})
            with urllib.request.urlopen(req, timeout=30) as r:
                content = json.loads(r.read())["content"]
        return meta["sha"], base64.b64decode(content)

    def _take_remote(self, path, rel, prefix):
        """Replace the local copy with the repo's, keeping the old one as a backup."""
        sha, data = self._remote(rel)
        if sha is None:
            return False
        local = read_bytes(path)
        if local != data:
            if local is not None and prefix:
                rotate_backup(path, prefix)
            atomic_write_bytes(path, data)
        self.shas[rel] = sha
        self.dirty.discard(rel)
        self.checked[rel] = time.monotonic()
        return local != data

    def refresh(self, path, prefix, max_age=None):
        """Pull the repo's copy if it changed since we last looked. Returns True if
        the local file changed. Never raises: if GitHub is unreachable the local
        copy is used as-is."""
        if not self.enabled:
            return False
        rel = self.repo_path(path)
        max_age = self.REFRESH_SECONDS if max_age is None else max_age
        with self.lock:
            if rel in self.dirty:
                try:
                    self.push(path, f"tracker: save {rel}")
                except SyncConflict:
                    return True   # push() already pulled the repo's version
                except SyncPending:
                    return False
            last = self.checked.get(rel)
            if last is not None and time.monotonic() - last < max_age:
                return False
            try:
                local = read_bytes(path)
                status, meta = self._call("GET", rel, params={"ref": self.branch})
                self.checked[rel] = time.monotonic()
                if status == 404:
                    return False
                if status != 200:
                    raise OSError(f"GitHub returned {status}")
                if local is not None and meta.get("sha") == git_blob_sha(local):
                    self.shas[rel] = meta["sha"]
                    return False
                return self._take_remote(path, rel, prefix)
            except (OSError, ValueError, KeyError) as e:
                print(f"[sync] couldn't check {rel} on GitHub: {e}", file=sys.stderr, flush=True)
                return False

    def push(self, path, message, overwrite=False):
        """Commit the local file to the repo. Raises SyncConflict if the repo copy
        changed since our last pull (the local file then holds the repo's
        version, and the version we tried to save is kept in backups/), or
        SyncPending if GitHub couldn't be reached. `overwrite` skips the check,
        for files only this server writes (uploaded PDFs)."""
        if not self.enabled:
            return
        rel = self.repo_path(path)
        data = read_bytes(path)
        if data is None:
            return
        with self.lock:
            try:
                if overwrite or rel not in self.shas:
                    # We don't know which repo version this copy came from (or don't care, for uploads).
                    status, meta = self._call("GET", rel, params={"ref": self.branch})
                    if status == 200:
                        if meta.get("sha") == git_blob_sha(data):
                            self.shas[rel] = meta["sha"]
                            self.dirty.discard(rel)
                            return  # the repo already has exactly this
                        if not overwrite:
                            self._conflict(path, rel)
                        self.shas[rel] = meta.get("sha")
                    elif status == 404:
                        self.shas.pop(rel, None)
                    else:
                        raise OSError(f"GitHub returned {status}")
                body = {"message": message, "branch": self.branch,
                        "content": base64.b64encode(data).decode("ascii")}
                if self.shas.get(rel):
                    body["sha"] = self.shas[rel]
                status, meta = self._call("PUT", rel, body)
            except OSError as e:
                self.dirty.add(rel)
                raise SyncPending(f"saved here, but not yet to GitHub ({e})") from e
            if status in (200, 201):
                self.shas[rel] = meta["content"]["sha"]
                self.dirty.discard(rel)
                self.checked[rel] = time.monotonic()
                return
            if status in (409, 422) and not overwrite:
                self._conflict(path, rel)
            self.dirty.add(rel)
            raise SyncPending(f"GitHub refused the save ({status}: {meta.get('message', '')})")

    def _conflict(self, path, rel):
        """Keep our version in backups/, take the repo's, and raise SyncConflict."""
        rotate_backup(path, os.path.splitext(os.path.basename(path))[0] + "-unsynced")
        try:
            self._take_remote(path, rel, None)
        except OSError:
            self.dirty.add(rel)
        raise SyncConflict("the copy on GitHub changed since this one was loaded")

    def startup(self, paths):
        """Pull the latest copy of each data file before serving anything."""
        if not self.enabled:
            return
        for path, prefix in paths:
            rel = self.repo_path(path)
            try:
                with self.lock:
                    changed = self._take_remote(path, rel, prefix)
                print(f"[sync] {rel}: {'pulled from GitHub' if changed else 'up to date'}", flush=True)
            except (OSError, ValueError, KeyError) as e:
                print(f"[sync] couldn't pull {rel} from GitHub, using the local copy: {e}",
                      file=sys.stderr, flush=True)


sync = GitHubSync.from_env()
