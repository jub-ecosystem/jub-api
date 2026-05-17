import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple
from cachetools import TTLCache


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
        """Build a full storage key from parts, prepending the namespace when set."""
        segments = [p for p in (self.namespace, *parts) if p]
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

    async def put(self, key: str, data: bytes) -> str:
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest)

    async def get(self, key: str) -> Tuple[bytes, bool]:
        if key in self._cache:
            return self._cache[key], True
        data = (self.base / key).read_bytes()
        self._cache[key] = data
        return data, False

    async def list(self, prefix: str) -> List[str]:
        root = self.base / prefix
        if not root.exists():
            return []
        files = sorted(root.rglob("*"), key=lambda p: p.stat().st_mtime)
        return [str(f.relative_to(self.base)) for f in files if f.is_file()]

    async def list_directories(self, prefix: str) -> List[str]:
        root = self.base / prefix
        if not root.exists():
            return []
        return [d.name for d in root.iterdir() if d.is_dir()]

    async def delete_prefix(self, prefix: str) -> int:
        root = self.base / prefix
        if not root.exists():
            return 0
        count = sum(1 for f in root.rglob("*") if f.is_file())
        shutil.rmtree(root)
        for key in list(self._cache):
            if key.startswith(prefix):
                self._cache.pop(key, None)
        return count
