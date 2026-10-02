import hashlib
import itertools
import re
import shutil
import time
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple
from cachetools import TTLCache


# Ids that end up as storage path segments (product_id, job_id, …): 1-128 of
# A-Z a-z 0-9 _ . - and not starting with "." (so never "." or "..").
SAFE_ID_PATTERN = r"^[A-Za-z0-9_\-][A-Za-z0-9_.\-]{0,127}$"
_SAFE_ID        = re.compile(SAFE_ID_PATTERN)


class InvalidStorageKey(ValueError):
    """Raised when a key or file name would resolve outside the storage namespace."""


def is_safe_id(value: str) -> bool:
    """True if *value* can be used as a single storage path segment."""
    return isinstance(value, str) and bool(_SAFE_ID.match(value))


def safe_filename(filename: str) -> str:
    """
    Reduces a client-supplied file name to its last path component
    ("../../etc/passwd" → "passwd", "C:\\x\\photo.jpg" → "photo.jpg").
    Raises InvalidStorageKey if nothing usable is left.
    """
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable())
    if name in ("", ".", ".."):
        raise InvalidStorageKey(f"Invalid file name: {filename!r}")
    return name[:255]


def _check_segment(segment: str) -> str:
    if not isinstance(segment, str) or segment in (".", "..") or any(ch in segment for ch in ("/", "\\", "\x00")):
        raise InvalidStorageKey(f"Invalid storage key segment: {segment!r}")
    return segment


class StorageBackend(ABC):
    """
    Abstract storage interface.  Swap implementations (local disk, S3, GCS, MictlanX, …)
    without touching any business logic.

    Subclasses MUST define `namespace` — the root prefix that scopes all keys for
    this backend (e.g. "products" for local disk, "" for a flat cloud bucket).
    Forgetting to define it raises TypeError at instantiation.
    """

    @property
    @abstractmethod
    def namespace(self) -> str:
        """Root prefix that scopes all keys.  Empty string means flat (no prefix)."""

    # ── Key helpers ────────────────────────────────────────────────────────────

    def key_for(self, *parts: str) -> str:
        """
        Build a full storage key from parts, prepending the namespace when set.
        Each part is ONE path segment: '/', '\\', '.', '..' and NUL are rejected
        with InvalidStorageKey, so ids and file names cannot escape the namespace.
        """
        segments = [_check_segment(p) for p in (self.namespace, *parts) if p]
        return "/".join(segments)

    def prefix_for(self, resource_id: str) -> str:
        """Return the prefix that covers all files belonging to *resource_id*."""
        return self.key_for(resource_id)

    # ── Abstract IO ────────────────────────────────────────────────────────────

    @abstractmethod
    async def put(self, key: str, data: bytes) -> str:
        """Persist *data* under *key* and return the canonical storage URI."""

    @abstractmethod
    async def get(self, key: str) -> Tuple[bytes, bool]:
        """Retrieve the bytes stored under *key*. Returns (data, cache_hit)."""

    @abstractmethod
    async def list(self, prefix: str) -> List[str]:
        """Return all keys that start with *prefix*, sorted oldest-first."""

    @abstractmethod
    async def list_directories(self, prefix: str) -> List[str]:
        """Return immediate child directory names under *prefix*."""

    @abstractmethod
    async def delete_prefix(self, prefix: str) -> int:
        """Delete all keys under *prefix* and return the number of files removed."""


class LocalStorageBackend(StorageBackend):
    """
    Stores files in a local directory tree.  Suitable for development and single-node
    deployments; replace with a cloud backend in production.
    """

    namespace = "products"

    def __init__(self, base_path: str = "/tmp/jub_storage", max_bytes: int = 200 * 1024 * 1024, ttl: int = 300):
        self.base   = Path(base_path)
        self._cache = TTLCache(maxsize=max_bytes, ttl=ttl, getsizeof=len)
        self.base.mkdir(parents=True, exist_ok=True)
        # Every key must resolve inside <base>/<namespace>.
        self._root  = (self.base / self.namespace).resolve()

    def _resolve(self, key: str) -> Path:
        """Absolute path of *key*; raises InvalidStorageKey if it escapes the namespace."""
        path = (self.base / key).resolve()
        if not path.is_relative_to(self._root):
            raise InvalidStorageKey(f"Storage key escapes the storage namespace: {key!r}")
        return path

    async def put(self, key: str, data: bytes) -> str:
        dest = self._resolve(key)
        if dest == self._root:
            raise InvalidStorageKey(f"Storage key has no file name: {key!r}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest)

    async def get(self, key: str) -> Tuple[bytes, bool]:
        path = self._resolve(key)
        if key in self._cache:
            return self._cache[key], True
        data = path.read_bytes()
        self._cache[key] = data
        return data, False

    async def list(self, prefix: str) -> List[str]:
        root = self._resolve(prefix)
        if not root.exists():
            return []
        files = sorted(root.rglob("*"), key=lambda p: p.stat().st_mtime)
        return [str(f.relative_to(self.base.resolve())) for f in files if f.is_file()]

    async def list_directories(self, prefix: str) -> List[str]:
        root = self._resolve(prefix)
        if not root.exists():
            return []
        return [d.name for d in root.iterdir() if d.is_dir()]

    async def delete_prefix(self, prefix: str) -> int:
        root = self._resolve(prefix)
        if root == self._root:
            raise InvalidStorageKey(f"Refusing to delete the whole storage namespace: {prefix!r}")
        if not root.exists():
            return 0
        count = sum(1 for f in root.rglob("*") if f.is_file())
        shutil.rmtree(root)
        for key in list(self._cache):
            if key == prefix or key.startswith(prefix.rstrip("/") + "/"):
                self._cache.pop(key, None)
        return count


def _check_key(namespace: str, key: str) -> str:
    """Validate a full key for backends without a real filesystem (memory, MictlanX)."""
    segments = key.split("/") if isinstance(key, str) else [key]
    for segment in segments:
        _check_segment(segment)
    if namespace and segments[0] != namespace:
        raise InvalidStorageKey(f"Storage key escapes the storage namespace: {key!r}")
    return key


def _under(key: str, prefix: str) -> bool:
    prefix = prefix.rstrip("/")
    return key == prefix or key.startswith(prefix + "/")


def _child_directories(keys: List[str], prefix: str) -> List[str]:
    """Immediate child "directory" names under *prefix* for a flat list of keys."""
    depth = len(prefix.rstrip("/").split("/"))
    names = []
    for key in keys:
        parts = key.split("/")
        # parts[depth] is a directory only if something is nested below it.
        if len(parts) > depth + 1 and parts[depth] not in names:
            names.append(parts[depth])
    return names


class InMemoryStorageBackend(StorageBackend):
    """
    Keeps files in a process-local dict.  Nothing survives a restart and nothing is
    shared between workers: use it for tests and quick local runs only.
    """

    namespace = "products"

    def __init__(self):
        self._files: Dict[str, Tuple[int, bytes]] = {}   # key -> (insertion seq, data)
        self._seq   = itertools.count()

    async def put(self, key: str, data: bytes) -> str:
        _check_key(self.namespace, key)
        if key == self.namespace:
            raise InvalidStorageKey(f"Storage key has no file name: {key!r}")
        self._files[key] = (next(self._seq), bytes(data))
        return f"memory://{key}"

    async def get(self, key: str) -> Tuple[bytes, bool]:
        _check_key(self.namespace, key)
        if key not in self._files:
            raise FileNotFoundError(key)
        return self._files[key][1], False

    async def list(self, prefix: str) -> List[str]:
        _check_key(self.namespace, prefix)
        keys = [k for k in self._files if _under(k, prefix) and k != prefix]
        return sorted(keys, key=lambda k: self._files[k][0])

    async def list_directories(self, prefix: str) -> List[str]:
        return _child_directories(await self.list(prefix), prefix)

    async def delete_prefix(self, prefix: str) -> int:
        _check_key(self.namespace, prefix)
        if prefix.rstrip("/") == self.namespace:
            raise InvalidStorageKey(f"Refusing to delete the whole storage namespace: {prefix!r}")
        keys = [k for k in self._files if _under(k, prefix)]
        for k in keys:
            del self._files[k]
        return len(keys)


class MictlanXStorageBackend(StorageBackend):
    """
    Stores files in a MictlanX bucket.  Every storage key becomes one ball whose id is
    sha256(key); the original key and upload time travel in the ball tags, which is
    what `list` uses to rebuild the directory-like view.
    """

    namespace = "products"

    def __init__(
        self,
        uri:       str,
        bucket_id: str = "jub",
        client_id: str = "jubapi",
        max_bytes: int = 200 * 1024 * 1024,
        ttl:       int = 300,
        client          = None,
    ):
        self.uri       = uri
        self.bucket_id = bucket_id
        self.client_id = client_id
        self._client   = client
        self._cache    = TTLCache(maxsize=max_bytes, ttl=ttl, getsizeof=len)

    @property
    def client(self):
        # Created lazily so importing jubapi never requires a reachable router.
        if self._client is None:
            from mictlanx import AsyncClient
            self._client = AsyncClient(uri=self.uri, client_id=self.client_id, debug=False)
        return self._client

    @staticmethod
    def ball_id(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    async def put(self, key: str, data: bytes) -> str:
        _check_key(self.namespace, key)
        if key == self.namespace:
            raise InvalidStorageKey(f"Storage key has no file name: {key!r}")
        ball_id = self.ball_id(key)
        res = await self.client.put(
            bucket_id = self.bucket_id,
            key       = ball_id,
            value     = bytes(data),
            tags      = {"jub_key": key, "jub_created_at": str(time.time_ns())},
        )
        if res.is_err:
            raise res.unwrap_err()
        self._cache.pop(key, None)
        return f"mictlanx://{self.bucket_id}/{ball_id}"

    async def get(self, key: str) -> Tuple[bytes, bool]:
        _check_key(self.namespace, key)
        if key in self._cache:
            return self._cache[key], True
        res = await self.client.get(bucket_id=self.bucket_id, key=self.ball_id(key))
        if res.is_err:
            raise res.unwrap_err()
        data = res.unwrap().data.tobytes()
        self._cache[key] = data
        return data, False

    async def _entries(self) -> List[Tuple[str, int]]:
        """(key, created_at) for every jub ball in the bucket."""
        res = await self.client.get_bucket_metadata(bucket_id=self.bucket_id)
        if res.is_err:
            err = res.unwrap_err()
            if getattr(err, "status_code", None) == 404:
                return []
            raise err
        entries = []
        for ball in res.unwrap():
            tags = ball.chunks[0].tags if ball.chunks else {}
            if "jub_key" in tags:
                entries.append((tags["jub_key"], int(tags.get("jub_created_at", "0"))))
        return entries

    async def list(self, prefix: str) -> List[str]:
        _check_key(self.namespace, prefix)
        entries = [(k, t) for k, t in await self._entries() if _under(k, prefix) and k != prefix]
        return [k for k, _ in sorted(entries, key=lambda e: e[1])]

    async def list_directories(self, prefix: str) -> List[str]:
        return _child_directories(await self.list(prefix), prefix)

    async def delete_prefix(self, prefix: str) -> int:
        _check_key(self.namespace, prefix)
        if prefix.rstrip("/") == self.namespace:
            raise InvalidStorageKey(f"Refusing to delete the whole storage namespace: {prefix!r}")
        keys = await self.list(prefix)
        for key in keys:
            res = await self.client.delete(ball_id=self.ball_id(key), bucket_id=self.bucket_id)
            if res.is_err:
                raise res.unwrap_err()
            self._cache.pop(key, None)
        return len(keys)


STORAGE_BACKENDS = ("FS", "MEMORY", "MICTLANX")


def create_storage_backend(
    kind:               str           = "FS",
    base_path:          str           = "/tmp/jub_storage",
    max_bytes:          int           = 200 * 1024 * 1024,
    ttl:                int           = 300,
    mictlanx_uri:       Optional[str] = None,
    mictlanx_bucket_id: str           = "jub",
    mictlanx_client_id: str           = "jubapi",
) -> StorageBackend:
    """Build the backend selected by *kind* (FS | MEMORY | MICTLANX)."""
    kind = (kind or "FS").strip().upper()
    if kind == "FS":
        return LocalStorageBackend(base_path=base_path, max_bytes=max_bytes, ttl=ttl)
    if kind == "MEMORY":
        return InMemoryStorageBackend()
    if kind == "MICTLANX":
        if not mictlanx_uri:
            raise ValueError("JUB_STORAGE_BACKEND=MICTLANX requires JUB_MICTLANX_URI")
        return MictlanXStorageBackend(
            uri=mictlanx_uri, bucket_id=mictlanx_bucket_id, client_id=mictlanx_client_id,
            max_bytes=max_bytes, ttl=ttl,
        )
    raise ValueError(f"Unknown JUB_STORAGE_BACKEND {kind!r}; expected one of {STORAGE_BACKENDS}")
