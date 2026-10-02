"""
08 — Tag products and search them
=================================

Tags are catalog item ids. Tagging "Mortalidad por COVID-19 por Estado" with
COVID_19 and the 32 states is what makes it show up for queries like
`jub.v1.VS(TAMS).VI(COVID_19)`.

    1. add_product_tags() / remove_product_tag()
    2. get_product_tags()          tag ids
       get_product_tag_details()   full catalog items behind the tags
    3. list_products_for_item()    reverse lookup: item → products
    4. search()                    DSL query over products

How identifiers are written in search:

    VS(TAMS)                               spatial: value
    VS(itm_1a2b3c4d.*)                     spatial: an item and its children
    VT(>= 2021)                            temporal: compared with temporal_value
    VI(CAUSA_DEFUNCION.COVID_19)           interest: CATALOG.VALUE
    VI(itm_1a2b3c4d)                       any block: the catalog_item_id

A bare VI(COVID_19) only matches items whose catalog_item_id is literally
"COVID_19" (as in the seed scripts), so with server-generated ids qualify
the value with its catalog, or use the id. Aliases (VS(Tamaulipas)) and
wildcard roots (VS(MX.*)) resolve to a single item across the whole
database, so once several catalogs share them they may pick another
catalog's item: use ids in that case.

Scoping the query with `observatory_id` restricts results to one
observatory — important here, because every run of these examples creates
items with the same values.

Run:
    python examples/client/advanced/08_tag_and_search.py
"""

import asyncio
from typing import Any

import jub.dto.v2 as DTO

import _domain as D
from _common import build_client, item_ids, require, unwrap


async def main() -> None:
    client   = await build_client()
    obs_id   = require("observatory_id", "04_observatories.py")
    products = require("products", "06_products.py")
    covid_product = products["mort_covid_estado"]   # created without tags in 06

    covid_id   = item_ids("causa_defuncion", ["COVID_19"])[0]
    years      = item_ids("temporal", [f"Y{y}" for y in range(2020, 2024)])
    states     = item_ids("spatial", [abbr for _, _, abbr, _ in D.MEXICO_STATES])
    mexico_id  = item_ids("spatial", ["MX"])[0]

    # ── 1. Tag ───────────────────────────────────────────────────────────
    new_tags = [covid_id, *years, *states]
    unwrap(await client.add_product_tags(covid_product, DTO.TagProductDTO(catalog_item_ids=new_tags)), "add tags")
    print(f"✓ [add_product_tags]   {len(new_tags)} tags added to {covid_product}")

    y2023 = item_ids("temporal", ["Y2023"])[0]
    unwrap(await client.remove_product_tag(covid_product, y2023), "remove tag Y2023")
    print("✓ [remove_product_tag] Y2023 removed")

    # ── 2. Read tags back ────────────────────────────────────────────────
    tags = unwrap(await client.get_product_tags(covid_product), "get tags")
    print(f"✓ [get_product_tags]   {len(tags.catalog_item_ids)} tag ids")

    details = unwrap(await client.get_product_tag_details(covid_product), "get tag details")
    by_type: dict[str, list[str]] = {}
    for it in details:
        by_type.setdefault(it.catalog_type or "?", []).append(it.value)
    print("✓ [get_product_tag_details]")
    for catalog_type, values in by_type.items():
        preview = ", ".join(sorted(values)[:6]) + (" …" if len(values) > 6 else "")
        print(f"    {catalog_type:<9} ({len(values):>2})  {preview}")

    # ── 3. Reverse lookup ────────────────────────────────────────────────
    for_item = unwrap(await client.list_products_for_item(covid_id), "list products for COVID_19")
    print(f"✓ [list_products_for_item] COVID_19 → {for_item.product_ids}")

    # ── 4. Search ────────────────────────────────────────────────────────
    queries = [
        ("interest",            "jub.v1.VI(CAUSA_DEFUNCION.COVID_19)"),
        ("by item id",          f"jub.v1.VI({covid_id})"),
        ("spatial subtree",     f"jub.v1.VS({mexico_id}.*)"),
        ("spatial + interest",  "jub.v1.VS(TAMS).VI(CAUSA_DEFUNCION.COVID_19)"),
        ("OR inside a block",   "jub.v1.VI(SEX.HOMBRE OR SEX.MUJER)"),
        ("temporal range",      "jub.v1.VT(>= 2021)"),
    ]
    print(f"\n[search] scoped to {obs_id}")
    for label, query in queries:
        results: list[dict[str, Any]] = unwrap(
            await client.search(DTO.SearchQueryDTO(query=query, observatory_id=obs_id, limit=20)),
            f"search {query}",
        )
        names = ", ".join(r.get("name", r.get("product_id", "?")) for r in results) or "—"
        print(f"  {label:<19} {query:<46} {len(results)} → {names}")


if __name__ == "__main__":
    asyncio.run(main())
