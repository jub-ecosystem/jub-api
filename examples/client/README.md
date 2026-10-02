# JUB client examples

Runnable examples of the `jub` Python client (`jub.client.v2`), from signing
up to publishing an observatory.

```
.env.examples           default API URL and user (invitado / invitado)
01_signup.py            create a new user, prints an export line to use it
02_authentication.py    log in
basics/                 03–12, simple: a car photo observatory
advanced/               03–12, every option: a public-health observatory
```

## Prerequisites

1. The stack running: `./run_local.sh` (MongoDB, Xolo, API on port 5000).
2. The `jub` scope created in Xolo: `./create_scope.sh`. Without it signup fails.
3. The `invitado` user (password `invitado`): `./create_user.sh`.
4. The client installed (already a dependency of this project):
   `poetry add --source test --allow-prereleases jub`. It brings
   `python-dotenv`, which the examples use to read `.env.examples`.
5. For `basics/`: the car photos in `source/cars` (in this repository).

## Configuration

Every script loads `examples/client/.env.examples`:

```sh
JUB_API_URL=http://localhost:5000
JUB_USERNAME=invitado
JUB_PASSWORD=invitado
```

Variables already set in your shell take precedence, so you can point the
examples at another API or user without editing the file:

```sh
export JUB_API_URL=http://my-server:5000
export JUB_USERNAME=demo_1a2b3c JUB_PASSWORD=...   # e.g. the user printed by 01
```

## Car photos (`basics/`)

The basics build the whole observatory from the photo file names:

```
source/cars/
  ford_mustang_blue_1968.jpg
  mitsubishi_eclipse_black_1998.jpg
  mitsubishi_eclipse_red_1998.jpg
  mitsubishi_eclipse_white_1998.jpg
  nissan_gtr_blue_1998.webp
  nissan_gtr_white_1998.avif
  toyota_supra_black_1997.jpg
  toyota_supra_red_1997.jpg
```

- Name: `brand_model_color_year.ext`, exactly four parts separated by `_`.
  Use `-` inside a part (`mercedes-benz_c-class_silver_2020.jpg`).
- Extension: `.jpg`, `.jpeg`, `.png`, `.webp` or `.avif`. Files without one
  are ignored.
- Each part becomes a catalog item: `CAR_BRAND` (with the model as a child),
  `CAR_COLOR`, `CAR_YEAR` (`Y1998`). With the photos above: FORD, MITSUBISHI,
  NISSAN, TOYOTA · BLACK, BLUE, RED, WHITE · Y1968, Y1997, Y1998.
- Each photo becomes one product, uploaded in 07/09.

To use other photos, replace the files and run the basics with a new user
(see [Running again](#running-again)). `03_catalogs.py` lists any file whose
name does not match.

## Run

```sh
python examples/client/01_signup.py             # optional: creates a new user
python examples/client/02_authentication.py

for f in examples/client/basics/[01]*.py; do python "$f" || break; done
for f in examples/client/advanced/[01]*.py; do python "$f" || break; done
```

Run the 03–12 scripts of a folder in order: each step uses what the previous
ones created.

| # | basics | advanced adds |
|---|--------|---------------|
| 03 | Brand/model, color, year and country catalogs; an item and an alias added later | JSON files, hierarchy built afterwards, one item in two catalogs |
| 04 | `setup_observatory` (disabled until 12) | `create_observatory` (enabled) |
| 05 | Link catalogs with a `level` | Unlink, create + link in bulk |
| 06 | One product per photo | Bulk creation, tags at creation, one product in two observatories |
| 07 | Upload a photo, wait for the task, download it | Upload bytes |
| 08 | Tag products, DSL search | Remove tags, tag details, item → products |
| 09 | Upload all photos with retries; run twice to see them skipped | A failing upload, `bulk_upload_products`, registry cleanup |
| 10 | Car sales data source, records, query | Chunked ingestion, aggregation with `generate_plot` |
| 11 | `index_service` | Step-by-step creation, `SVC()` search |
| 12 | Review and publish | Checklist, tasks, stats |

## How the steps share ids

- **basics** chooses its own ids from the username (`cars_<user>`,
  `brands_<user>`, `TOYOTA_<user>`, …), so no files are shared between scripts.
- **advanced** lets the server generate ids and stores them in
  `advanced/.state.json` (git-ignored). The state belongs to the current user.

## Running again

The ids depend on the user, so each user can build each example observatory
once: a second run as `invitado` stops in `basics/03` (the catalogs already
exist) or `advanced/04` (the observatory already exists). To run them again,
create a new user and use it:

```sh
python examples/client/01_signup.py
export JUB_USERNAME=... JUB_PASSWORD=...        # the line printed by 01
```

## Search tips

The same values (`TOYOTA`, `MX`, …) can exist in many catalogs — every run of
these examples creates new ones. So the examples:

- scope searches with `observatory_id`;
- write interest filters as `VI(CATALOG.VALUE)`, e.g. `VI(CAR_BRAND.TOYOTA)`;
- use catalog item ids in data source queries, and for aliases and wildcards.
