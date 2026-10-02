"""
03 — Catalogs, items and aliases
================================

Catalogs are the vocabularies observatories, products and data records are
described with. Every catalog has a type:

    SPATIAL   where      (country → state → municipality)
    TEMPORAL  when       (years, months, …)
    INTEREST  what       (sex, age group, cause of death, …)

A catalog holds *items*. Each item has a `value` (UPPER_SNAKE_CASE, used in DSL
queries), a numeric `code`, optional *aliases* (other names that resolve to the
same item, e.g. "Tamaulipas" or "28" → TAMS) and optional *children* (hierarchy).

This example shows every way of building them:

    1. create_catalog()            nested payload: items + aliases + children in one call
    2. create_catalog_from_json()  same, loaded from fixtures/causa_defuncion.json
    3. create_catalog_item()       add items one by one to an existing catalog
    4. add_catalog_item_alias()    add aliases to an existing item
    5. parent_item_id / link_catalog_item_child()   extend a hierarchy afterwards
    6. link_item_to_catalog()      reuse the same item in a second catalog

The catalog and item ids are saved to .state.json for the next steps.

Run:
    python examples/client/advanced/03_catalogs.py
"""

import asyncio

import jub.dto.v2 as DTO

import _domain as D
from _common import FIXTURES_DIR, build_client, index_catalog_items, save_state, unwrap


async def main() -> None:
    client = await build_client()
    catalog_ids: dict[str, str] = {}

    # ── 1. Nested payload: items, aliases and hierarchy in a single call ───
    for key, payload in [
        ("spatial",   D.spatial_catalog()),     # Mexico → 32 states, with aliases
        ("sex",       D.sex_catalog()),
        ("age_group", D.age_group_catalog()),
    ]:
        created = unwrap(await client.create_catalog(DTO.CatalogCreateDTO(**payload)), f"create catalog {key}")
        catalog_ids[key] = created.catalog_id
        print(f"✓ [create_catalog]           {key:<16} → {created.catalog_id}")

    # ── 2. Same payload shape, loaded from a JSON file ─────────────────────
    created = unwrap(
        await client.create_catalog_from_json(json_path=str(FIXTURES_DIR / "causa_defuncion.json")),
        "create catalog from JSON",
    )
    catalog_ids["causa_defuncion"] = created.catalog_id
    print(f"✓ [create_catalog_from_json] causa_defuncion  → {created.catalog_id}")

    # ── 3. Empty catalog + items added one by one ──────────────────────────
    created = unwrap(
        await client.create_catalog(DTO.CatalogCreateDTO(
            name         = "Dimension Temporal — Años de Reporte",
            value        = "TEMPORAL_ANIOS",
            catalog_type = "TEMPORAL",
            description  = "Años calendario 2015-2023.",
        )),
        "create temporal catalog",
    )
    catalog_ids["temporal"] = created.catalog_id

    for year in D.YEARS:
        year_item = unwrap(
            await client.create_catalog_item(DTO.CatalogItemStandaloneCreateDTO(
                catalog_id     = catalog_ids["temporal"],   # the item is linked to this catalog
                name           = str(year),
                value          = f"Y{year}",
                code           = year,
                value_type     = "DATETIME",
                temporal_value = f"{year}-01-01T00:00:00Z",  # what VT(>= 2020) compares against
            )),
            f"create item Y{year}",
        )
        # ── 4. Alias on an existing item: VT/VI(2020) resolves to Y2020 ────
        unwrap(
            await client.add_catalog_item_alias(
                year_item.catalog_item_id,
                DTO.CatalogItemAliasCreateDTO(value=str(year), value_type="NUMBER", description="Año como entero"),
            ),
            f"add alias to Y{year}",
        )
    print(f"✓ [create_catalog_item]      temporal         → {catalog_ids['temporal']} ({len(D.YEARS)} years + 1 alias each)")

    # Resolve the ids the server generated for the nested spatial items.
    spatial = unwrap(await client.get_catalog(catalog_ids["spatial"]), "get spatial catalog")
    spatial_items = index_catalog_items(spatial)
    tams_id = spatial_items["TAMS"]

    # Another alias on an item created in step 1.
    unwrap(
        await client.add_catalog_item_alias(tams_id, DTO.CatalogItemAliasCreateDTO(value="Tamps", value_type="STRING", description="Abreviatura comun")),
        "add alias to TAMS",
    )
    aliases = unwrap(await client.list_catalog_item_aliases(tams_id), "list TAMS aliases")
    print(f"✓ [add_catalog_item_alias]   TAMS aliases     → {', '.join(a.value for a in aliases)}")

    # ── 5. Extend the hierarchy: Tamaulipas → municipalities ────────────────
    # a) parent_item_id at creation time
    unwrap(
        await client.create_catalog_item(DTO.CatalogItemStandaloneCreateDTO(
            catalog_id     = catalog_ids["spatial"],
            parent_item_id = tams_id,
            name           = "Ciudad Victoria",
            value          = "TAMS_VICTORIA",
            code           = 28041,
            value_type     = "STRING",
        )),
        "create Ciudad Victoria",
    )
    # b) create first, link as a child afterwards
    tampico = unwrap(
        await client.create_catalog_item(DTO.CatalogItemStandaloneCreateDTO(
            catalog_id = catalog_ids["spatial"],
            name       = "Tampico",
            value      = "TAMS_TAMPICO",
            code       = 28038,
            value_type = "STRING",
        )),
        "create Tampico",
    )
    unwrap(
        await client.link_catalog_item_child(tams_id, DTO.CatalogItemChildLinkCreateDTO(child_item_id=tampico.catalog_item_id)),
        "link Tampico under TAMS",
    )
    children = unwrap(await client.list_catalog_item_children(tams_id), "list TAMS children")
    print(f"✓ [hierarchy]                TAMS children    → {', '.join(c.name for c in children)}")

    # ── 6. One item, two catalogs ──────────────────────────────────────────
    created = unwrap(
        await client.create_catalog(DTO.CatalogCreateDTO(
            name         = "Frontera Norte",
            value        = "FRONTERA_NORTE",
            catalog_type = "SPATIAL",
            description  = "Estados fronterizos con Estados Unidos.",
        )),
        "create Frontera Norte catalog",
    )
    catalog_ids["frontera_norte"] = created.catalog_id
    for abbr in D.NORTHERN_BORDER_STATES:
        unwrap(
            await client.link_item_to_catalog(spatial_items[abbr], DTO.CatalogItemCatalogLinkCreateDTO(catalog_id=catalog_ids["frontera_norte"])),
            f"link {abbr} to Frontera Norte",
        )
    in_catalogs = unwrap(await client.list_catalogs_for_item(tams_id), "list catalogs for TAMS")
    print(f"✓ [link_item_to_catalog]     TAMS belongs to  → {', '.join(c.value for c in in_catalogs)}")

    # ── Save {catalog: {item value: item id}} for the next steps ──────────
    items: dict[str, dict[str, str]] = {}
    for key, catalog_id in catalog_ids.items():
        catalog = unwrap(await client.get_catalog(catalog_id), f"get catalog {key}")
        items[key] = index_catalog_items(catalog)

    save_state(catalogs=catalog_ids, items=items)
    print(f"\nSaved {len(catalog_ids)} catalogs and {sum(map(len, items.values()))} item ids to .state.json")


if __name__ == "__main__":
    asyncio.run(main())
