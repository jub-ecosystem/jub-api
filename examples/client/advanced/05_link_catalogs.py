"""
05 — Link catalogs to observatories
===================================

Catalogs live on their own and are *linked* to observatories, so one catalog
(e.g. the Mexico spatial hierarchy) can be shared by many observatories.
Each link carries a `level`: the depth of the catalog in the observatory's
catalog hierarchy (0 = root).

    1. link_catalog_to_observatory()               link existing catalogs one by one
    2. unlink_catalog_from_observatory()           remove a link (catalog is kept)
    3. create_bulk_catalogs_and_link_from_json()   create + link from a JSON list
    4. bulk_assign_catalogs()                      create + link from DTOs
    5. list_observatory_catalogs()                 what an observatory exposes

Run:
    python examples/client/advanced/05_link_catalogs.py
"""

import asyncio

import jub.dto.v2 as DTO

import _domain as D
from _common import FIXTURES_DIR, build_client, index_catalog_items, require, save_state, unwrap

# catalog key (from 03) → level in the main observatory
MAIN_CATALOG_LEVELS = {
    "spatial":         0,
    "temporal":        1,
    "sex":             2,
    "age_group":       3,
    "causa_defuncion": 4,
}


async def main() -> None:
    client       = await build_client()
    obs_id       = require("observatory_id", "04_observatories.py")
    secondary_id = require("secondary_observatory_id", "04_observatories.py")
    catalog_ids  = dict(require("catalogs", "03_catalogs.py"))
    items        = dict(require("items", "03_catalogs.py"))

    # ── 1. Link existing catalogs one by one ──────────────────────────────
    for key, level in MAIN_CATALOG_LEVELS.items():
        unwrap(
            await client.link_catalog_to_observatory(obs_id, DTO.LinkCatalogDTO(catalog_id=catalog_ids[key], level=level)),
            f"link {key}",
        )
        print(f"✓ [link_catalog_to_observatory] {key:<16} level={level} → {obs_id}")

    # The same catalogs can be shared with another observatory.
    for key in ("spatial", "temporal", "sex"):
        unwrap(
            await client.link_catalog_to_observatory(secondary_id, DTO.LinkCatalogDTO(catalog_id=catalog_ids[key], level=MAIN_CATALOG_LEVELS[key])),
            f"link {key} to secondary",
        )
    print(f"✓ [link_catalog_to_observatory] spatial, temporal, sex also → {secondary_id}")

    # ── 2. Unlink: only the edge is removed, the catalog still exists ─────
    unwrap(
        await client.link_catalog_to_observatory(obs_id, DTO.LinkCatalogDTO(catalog_id=catalog_ids["frontera_norte"], level=1)),
        "link frontera_norte",
    )
    unwrap(await client.unlink_catalog_from_observatory(obs_id, catalog_ids["frontera_norte"]), "unlink frontera_norte")
    print(f"✓ [unlink_catalog_from_observatory] frontera_norte linked and unlinked")

    # ── 3. Create + link in one request, from a JSON list ─────────────────
    bulk = unwrap(
        await client.create_bulk_catalogs_and_link_from_json(obs_id, json_path=str(FIXTURES_DIR / "derechohabiencia.json")),
        "create + link derechohabiencia",
    )
    catalog_ids["derechohabiencia"] = bulk.catalog_ids[0]
    print(f"✓ [create_bulk_catalogs_and_link_from_json] derechohabiencia → {bulk.catalog_ids[0]}")

    # ── 4. Create + link in one request, from DTOs ────────────────────────
    cie10 = DTO.CatalogCreateDTO(
        name         = "Cancer por Tipo CIE-10",
        value        = "CIE10_CANCER",
        catalog_type = "INTEREST",
        description  = "Tipos de cancer mas frecuentes segun CIE-10.",
        items        = [
            DTO.CatalogItemCreateDTO(**D.item("Cancer de mama",     "C_MAMA",       1, aliases=[D.alias("C50", "STRING", "CIE-10")])),
            DTO.CatalogItemCreateDTO(**D.item("Cancer de prostata", "C_PROSTATA",   2, aliases=[D.alias("C61", "STRING", "CIE-10")])),
            DTO.CatalogItemCreateDTO(**D.item("Cancer cervicouterino", "C_CERVIX",  3, aliases=[D.alias("C53", "STRING", "CIE-10")])),
            DTO.CatalogItemCreateDTO(**D.item("Cancer de pulmon",   "C_PULMON",     4, aliases=[D.alias("C34", "STRING", "CIE-10")])),
        ],
    )
    bulk = unwrap(
        await client.bulk_assign_catalogs(secondary_id, DTO.BulkCatalogsDTO(catalogs=[cie10])),
        "bulk assign cie10",
    )
    catalog_ids["cie10_cancer"] = bulk.catalog_ids[0]
    print(f"✓ [bulk_assign_catalogs] cie10_cancer → {bulk.catalog_ids[0]} (linked to {bulk.observatory_id})")

    # Store item ids of the new catalogs for 06/08/10.
    for key in ("derechohabiencia", "cie10_cancer"):
        catalog = unwrap(await client.get_catalog(catalog_ids[key]), f"get catalog {key}")
        items[key] = index_catalog_items(catalog)
    save_state(catalogs=catalog_ids, items=items)

    # ── 5. What each observatory exposes ──────────────────────────────────
    for oid in (obs_id, secondary_id):
        linked = unwrap(await client.list_observatory_catalogs(oid), f"list catalogs of {oid}")
        print(f"\n{oid}")
        for c in sorted(linked, key=lambda c: c.level):
            print(f"  level {c.level}  {c.catalog_type:<8}  {c.value:<18} {c.name}")


if __name__ == "__main__":
    asyncio.run(main())
