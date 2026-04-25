from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class StorageBackend(ABC):
    """
    Abstract storage interface.  Swap implementations (local disk, S3, GCS, MictlanX, …)
    without touching any business logic.
    """

    @abstractmethod
    async def put(self, key: str, data: bytes) -> str:
        """Persist *data* under *key* and return the canonical storage URI."""

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve the bytes stored under *key*."""

    @abstractmethod
    async def list(self, prefix: str) -> List[str]:
        """Return all keys that start with *prefix*, sorted oldest-first."""


class LocalStorageBackend(StorageBackend):
    """
    Stores files in a local directory tree.  Suitable for development and single-node
    deployments; replace with a cloud backend in production.
    """

    def __init__(self, base_path: str = "/tmp/jub_storage"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, data: bytes) -> str:
        dest = self.base / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest)

    async def get(self, key: str) -> bytes:
        return (self.base / key).read_bytes()

    async def list(self, prefix: str) -> List[str]:
        root = self.base / prefix
        if not root.exists():
            return []
        files = sorted(root.rglob("*"), key=lambda p: p.stat().st_mtime)
        return [str(f.relative_to(self.base)) for f in files if f.is_file()]
