# Query Language (DSL)

The JUB DSL is a concise string-based language for expressing multi-dimensional queries.
All strings must start with the prefix `jub.v1.`.

---

## Variable types

| Prefix | Full name | Role in query |
|---|---|---|
| `VS` | Spatial variable | Filter by geographic dimension |
| `VT` | Temporal variable | Filter by time dimension |
| `VI` | Interest variable | Filter by categorical dimension |
| `VO` | Observable variable | Define the metric to calculate |
| `BY` | Grouping variable | Group results by a catalog dimension |

---

## Syntax

### Basic structure

```
jub.v1.VS(...).VT(...).VI(...).VO(...).BY(...)
```

Each variable block is optional. Blocks are separated by `.` and evaluated independently.
Order does not matter.

### Boolean logic inside a block

```
VS(MX OR AGS)           # OR logic — match either
VT(>= 2020 AND <= 2025) # AND logic — intersection (range)
VI(SEX_MALE)            # SINGLE value
```

!!! note
    `AND` inside `VS()` is not allowed — a record has exactly one spatial location.

### Comparison operators (VT and VI)

```
=   !=   >   >=   <   <=
```

### Wildcards

```
VS(MX.*)     # All children of MX in the hierarchy
VS(*)        # No spatial filter (match everything)
```

---

## VS — Spatial filter

Filters records by `spatial_id`. The value provided is resolved to a `catalog_item_id`
before building the query.

```
jub.v1.VS(MX)
jub.v1.VS(MX OR AGS OR TAM)
jub.v1.VS(MX.*)
```

---

## VT — Temporal filter

Filters records by `temporal_id` (a datetime field).

Partial date strings are automatically padded:

| Input | Expands to |
|---|---|
| `2020` | `2020-01-01T00:00:00Z` |
| `2020-05` | `2020-05-01T00:00:00Z` |
| `2020-05-15` | `2020-05-15T00:00:00Z` |

```
jub.v1.VT(2025)                        # exact year
jub.v1.VT(>= 2020 AND <= 2025)        # range
jub.v1.VT(2022 OR 2023)               # specific years
jub.v1.VT(>= 2020-01 AND <= 2020-06)  # month range
```

---

## VI — Interest filter

Filters records by `interest_ids`. Each value is resolved to a `catalog_item_id`.

```
jub.v1.VI(SEX_FEMALE)
jub.v1.VI(C_MAMA OR C_OVARIO OR C_CERVIX)
jub.v1.VI(SEX_FEMALE AND C_MAMA)         # record must have BOTH
jub.v1.VI(AGE >= 20)                     # numeric comparison against code
jub.v1.VI(CIE10.C50)                     # hierarchical path: catalog.item
```

---

## VO — Observable (metric)

Defines what to calculate over the filtered records.

| Syntax | Result |
|---|---|
| `VO(COUNT)` | Count of matching records |
| `VO(SUM(TASA_100K))` | Sum of `numerical_interest_ids.TASA_100K` |
| `VO(AVG(TASA_100K))` | Average of `numerical_interest_ids.TASA_100K` |

When `VO()` is omitted, `COUNT` is used as the default.

```
jub.v1.VS(MX).VO(COUNT)
jub.v1.VI(C_MAMA).VO(AVG(TASA_100K))
```

---

## BY — Grouping

Groups the aggregation by a catalog dimension. The result has one entry per distinct
catalog item found in `interest_ids`.

```
jub.v1.VO(COUNT).BY(CIE10_CANCER)
jub.v1.VO(AVG(TASA_100K)).BY(CIE10_CANCER)
jub.v1.VO(COUNT).BY(TEMPORAL)
jub.v1.VO(COUNT).BY(SPATIAL)
```

`BY(CATALOG_VALUE)` looks up the catalog whose `value` equals `CATALOG_VALUE`, fetches all
its `catalog_item_ids`, and groups records by whichever of those IDs appears in `interest_ids`.

!!! important "Catalog membership — not ID prefix"
    `BY()` uses **catalog membership** (a DB lookup), not string prefix matching.
    You do not need to format `catalog_item_id` values with a specific prefix.

---

## Identifier resolution

When you pass a raw string to `VS()`, `VI()`, or `BY()`, the engine resolves it to a
`catalog_item_id` through the following priority chain:

1. **Exact `catalog_item_id` match** — fastest path
2. **`value` match** (normalised to `UPPER_SNAKE_CASE`)
3. **Numeric `code` match** (only when the input is a number)
4. **Alias `value` match** — checks `catalog_item_aliases`
5. **Alias `code` match** (numeric)
6. **Alias `catalog_item_alias_id` match**
7. **Raw string fallback** — returned unchanged (backward-compatible)

This means all of the following resolve to the same record set, assuming the catalog is
set up correctly:

```
jub.v1.VS(MX)          # value field = "MX"
jub.v1.VS(9)           # code = 9
jub.v1.VS(Mexico)      # alias value = "Mexico"
jub.v1.VS(cat_item_id) # direct catalog_item_id
```

---

## Complete examples

### Count all records from two states

```
jub.v1.VS(MX OR AGS)
```

### Temporal range + spatial filter

```
jub.v1.VS(TAM).VT(>= 2020 AND <= 2025)
```

### Female breast cancer records in 2023

```
jub.v1.VS(MX).VT(2023).VI(SEX_FEMALE AND C_MAMA)
```

### Average rate per 100k by cancer type

```
jub.v1.VS(MX).VI(C_MAMA OR C_OVARIO OR C_CERVIX).VO(AVG(TASA_100K)).BY(CIE10_CANCER)
```

### Count by year (temporal grouping)

```
jub.v1.VS(MX).VI(C_MAMA).VO(COUNT).BY(TEMPORAL)
```

### Count by state (spatial grouping)

```
jub.v1.VI(C_MAMA).VO(COUNT).BY(SPATIAL)
```

### Multi-dimensional: filter + aggregate

```
jub.v1.VS(MX OR AGS).VT(>= 2022).VI(C_MAMA OR C_OVARIO OR C_CERVIX OR C_PROSTATA).VO(AVG(TASA_100K)).BY(CIE10_CANCER)
```

---

## Endpoint mapping

| Use case | Endpoint | Notes |
|---|---|---|
| Search products | `POST /search` | Returns `ProductXDTO` list |
| Fetch raw records | `POST /search/records` | Returns `DataRecord` documents |
| Generate ECharts plot | `POST /search/plot` | Returns ECharts-ready JSON |
| Query source records | `POST /datasources/{id}/query` | Scoped to one source |
