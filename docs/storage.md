# Storage Backend

JUB API uses an abstract `StorageBackend` to persist uploaded product files.
The abstraction lets you swap storage providers (local disk, AWS S3, GCS, MictlanX, etc.)
without changing any service or controller code.

---

## Interface

```python
# jubapi/storage/__init__.py

from abc import ABC, abstractmethod

class StorageBackend(ABC):

    @abstractmethod
    async def put(self, key: str, data: bytes) -> str:
        """
        Persist *data* under *key* and return the canonical storage URI.
        The URI is stored alongside the task and can be passed to indexing systems.
        """

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve the bytes previously stored under *key*."""
```

---

## Default implementation — `LocalStorageBackend`

The default backend writes files to the local filesystem.
Suitable for development and single-node deployments.

```python
class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str = "/tmp/jub_storage"):
        ...

    async def put(self, key: str, data: bytes) -> str:
        # writes to /tmp/jub_storage/<key>
        # returns the absolute file path

    async def get(self, key: str) -> bytes:
        # reads from /tmp/jub_storage/<key>
```

---

## Key format

Files are stored under a deterministic key:

```
products/{product_id}/{job_id}/{original_filename}
```

Example:
```
products/p_001/tsk_upload_001/breast_cancer_2024.csv
```

---

## How to swap the backend

1. Create a new class that extends `StorageBackend` and implements `put` and `get`.

2. Replace the singleton in `jubapi/middlewares/__init__.py`:

```python
# Before
_storage_backend: StorageBackend = LocalStorageBackend()

# After — e.g. S3
_storage_backend: StorageBackend = S3StorageBackend(
    bucket="jub-data",
    region="us-east-1",
)
```

No other code changes are required.

---

## Example — S3 backend

```python
import aioboto3
from jubapi.storage import StorageBackend

class S3StorageBackend(StorageBackend):
    def __init__(self, bucket: str, region: str):
        self.bucket = bucket
        self.region = region

    async def put(self, key: str, data: bytes) -> str:
        session = aioboto3.Session()
        async with session.client("s3", region_name=self.region) as s3:
            await s3.put_object(Bucket=self.bucket, Key=key, Body=data)
        return f"s3://{self.bucket}/{key}"

    async def get(self, key: str) -> bytes:
        session = aioboto3.Session()
        async with session.client("s3", region_name=self.region) as s3:
            resp = await s3.get_object(Bucket=self.bucket, Key=key)
            return await resp["Body"].read()
```

---

## Upload flow

```
POST /products/{id}/upload  (multipart: user_id + file)
         │
         ├─ 1. Read file bytes from UploadFile
         ├─ 2. Create TaskX (PENDING / INDEX)
         ├─ 3. Return 202 immediately with { job_id, product_id, status: "queued" }
         │
         └─ BackgroundTask:
               ├─ storage.put(key, bytes)   ← StorageBackend.put()
               ├─ On success: task_svc.complete_task(job_id, success=True)
               └─ On failure: task_svc.complete_task(job_id, success=False, error_msg=...)
```

The caller can poll `GET /tasks/{job_id}` to track the background job.
Once the file is stored, an external indexing system reads it, processes the data,
and calls `POST /tasks/{job_id}/complete` when finished.
