from abc import ABC, abstractmethod
from pathlib import Path


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
