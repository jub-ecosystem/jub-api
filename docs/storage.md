# Storage Backend

Product files (uploaded via `POST /api/v2/products/{product_id}/upload`) are stored through a
small storage abstraction in `jubapi/storage/__init__.py`. Business logic only talks to the
`StorageBackend` interface, so the place where bytes live can be changed with one environment
variable.

## How it works

```
controller / service / orphan job
            │
            ▼
      StorageBackend  (abstract)
      ├── LocalStorageBackend     FS        files on disk (default)
      ├── InMemoryStorageBackend  MEMORY    python dict, lost on restart
      └── MictlanXStorageBackend  MICTLANX  balls in a MictlanX bucket
```

Every file is addressed by a **key** made of path segments:

```
products/<product_id>/<job_id>/<filename>
└──┬───┘
namespace
```

Keys are always built with `storage.key_for(...)`, which rejects `/`, `\`, `.`, `..` and NUL in a
segment, so ids and file names can never escape the `products` namespace.

The interface (all methods are `async`):

| Method | What it does |
|---|---|
| `put(key, data)` | Store bytes, return a URI for the stored object |
| `get(key)` | Return `(data, cache_hit)` |
| `list(prefix)` | All keys under `prefix`, oldest first (download picks the last one) |
| `list_directories(prefix)` | Immediate child names, e.g. product ids under `products` |
| `delete_prefix(prefix)` | Delete everything under `prefix`; refuses to wipe the whole namespace |

The single backend instance is created in `jubapi/middlewares/__init__.py` by
`create_storage_backend(...)` and injected with `Depends(MX.get_storage_backend)`.

## Selecting a backend

| Variable | Default | Used by | Purpose |
|---|---|---|---|
| `JUB_STORAGE_BACKEND` | `FS` | all | `FS`, `MEMORY` or `MICTLANX` (case-insensitive) |
| `JUB_STORAGE_PATH` | `/jub` | FS | Base directory; files go to `<path>/products/...` |
| `JUB_STORAGE_CACHE_MAX_BYTES` | 4 GB | FS, MICTLANX | Size of the read cache |
| `JUB_STORAGE_CACHE_TTL` | `300` | FS, MICTLANX | Read cache TTL (seconds) |
| `JUB_MICTLANX_URI` | – (required for MICTLANX) | MICTLANX | Router URI |
| `JUB_MICTLANX_BUCKET_ID` | `jub` | MICTLANX | Bucket where balls are stored |
| `JUB_MICTLANX_CLIENT_ID` | `jubapi` | MICTLANX | Client id used in MictlanX logs |

An unknown `JUB_STORAGE_BACKEND`, or `MICTLANX` without `JUB_MICTLANX_URI`, raises a `ValueError`
at startup instead of failing later on the first upload.

### FS (default)

Nothing to change. Example `.env`:

```sh
JUB_STORAGE_BACKEND=FS
JUB_STORAGE_PATH=/jub
```

In code:

```python
from jubapi.storage import LocalStorageBackend

storage = LocalStorageBackend(base_path="/tmp/jub_storage")
key = storage.key_for("product-1", "job-1", "photo.jpg")   # products/product-1/job-1/photo.jpg
await storage.put(key, b"...")
data, from_cache = await storage.get(key)
```

### MEMORY

Good for tests or a quick run without disk. Data is lost on restart and is **not** shared
between uvicorn workers.

```sh
JUB_STORAGE_BACKEND=MEMORY
```

```python
from jubapi.storage import InMemoryStorageBackend

storage = InMemoryStorageBackend()
await storage.put(storage.key_for("product-1", "job-1", "a.csv"), b"x,y\n1,2\n")
```

### MICTLANX

1. Start a MictlanX router + peers (from the mictlanx repo):

   ```sh
   cd mictlanx   # your clone of the MictlanX repo
   chmod +x ./deploy_router.sh && ./deploy_router.sh
   ```

2. Point Jub to it:

   ```sh
   JUB_STORAGE_BACKEND=MICTLANX
   JUB_MICTLANX_URI=mictlanx://mictlanx-router-0@localhost:60666/?protocol=http&api_version=4&http2=0
   JUB_MICTLANX_BUCKET_ID=jub
   ```

   If Jub runs in Docker, replace `localhost` with the router's host name on the Docker network.
   For several routers, separate them with commas:
   `mictlanx://mictlanx-router-0@host-a:60666,mictlanx-router-1@host-b:60667/?protocol=http&api_version=4&http2=0`.

3. Run the API as usual (`./run_local.sh`).

How it maps onto MictlanX:

- Each Jub key becomes one **ball** in `JUB_MICTLANX_BUCKET_ID`. The ball id is
  `sha256(key)`, so file names with any characters are safe.
- The original key and the upload time are stored in the ball tags (`jub_key`,
  `jub_created_at`). `list` reads the bucket metadata and uses those tags to rebuild the folder
  view and the oldest-first order.
- `delete_prefix` deletes each matching ball.
- The `AsyncClient` is created lazily on first use, so the API starts even if the router is not
  reachable yet (the first upload/download will fail instead).

Using the backend directly:

```python
import asyncio
from jubapi.storage import MictlanXStorageBackend

async def main():
    storage = MictlanXStorageBackend(
        uri       = "mictlanx://mictlanx-router-0@localhost:60666/?protocol=http&api_version=4&http2=0",
        bucket_id = "jub",
    )
    key = storage.key_for("product-1", "job-1", "hello.txt")
    print(await storage.put(key, b"hello"))            # mictlanx://jub/<sha256>
    print(await storage.list(storage.prefix_for("product-1")))
    data, _ = await storage.get(key)
    print(data)
    print(await storage.delete_prefix(storage.prefix_for("product-1")))

asyncio.run(main())
```

Which is the same as using the MictlanX client by hand:

```python
from mictlanx import AsyncClient

client = AsyncClient(uri=uri, client_id="jubapi", debug=False)
await client.put(bucket_id="jub", key=ball_id, value=data, tags={"jub_key": key})
res  = await client.get(bucket_id="jub", key=ball_id)
data = res.unwrap().data.tobytes()
```

Notes:

- `list` fetches the whole bucket's metadata, so use a dedicated bucket for Jub to keep it small.
- Other client settings (logging, cache, SSL) can still be tuned with the MictlanX
  `MICTLANX_CLIENT_*` / `MICTLANX_LOG_*` environment variables.

## Adding another backend

1. Subclass `StorageBackend`, set `namespace = "products"` and implement the five async methods.
   Validate keys with `key_for`/`_check_key` so nothing escapes the namespace.
2. Add a branch in `create_storage_backend` and its name to `STORAGE_BACKENDS`.
3. Add any new settings to `jubapi/config/__init__.py`, to the table above and to
   [Configuration](configuration.md).

## Upload flow

```
POST /api/v2/products/{product_id}/upload   (multipart: file, Bearer token)
         │
         ├─ 1. Reduce the file name to its last component (safe_filename)
         ├─ 2. Check the product exists
         ├─ 3. Create a TaskX (operation INDEX) owned by the current user
         ├─ 4. Return 202 immediately with { job_id, product_id }
         │
         └─ BackgroundTask:
               ├─ storage.put(storage.key_for(product_id, job_id, filename), bytes)
               ├─ Set metadata.extension on the product from the file extension
               ├─ On success: task_svc.complete_task(job_id, success=True)
               └─ On failure: task_svc.complete_task(job_id, success=False, error_msg=...)
```

The caller can poll `GET /api/v2/tasks/{job_id}` to track the background job.
Once the file is stored, an external indexing system reads it, processes the data,
and calls `POST /api/v2/tasks/{job_id}/complete` when finished.

`GET /api/v2/products/{product_id}/download` returns the latest uploaded file
(or the one for `?job_id=`), served from the backend's read cache when possible.

## Orphaned files

When `JUB_ORPHAN_CHECK_ENABLED=1`, a background job runs every
`JUB_ORPHAN_CHECK_INTERVAL_SECONDS`. It lists the product directories in storage and
reports those whose product no longer exists in MongoDB. With
`JUB_ORPHAN_CHECK_DELETE=1` it also deletes them; otherwise it only logs them.
