"""
06 — Products
=============

A product is a published analysis (a chart, a report, …) that belongs to an
observatory and is tagged with catalog items so it can be found by search (08).

    1. create_product()                one product: create + link to its observatory
                                       + tag it, all in one call
    2. bulk_assign_products()          many products for one observatory at once
    3. link_product_to_observatory()   share an existing product with another observatory
    4. list_observatory_products()

Products get their files in 07 (upload) and 09 (bulk upload with retries).

Run:
    python examples/client/advanced/06_products.py
"""

import asyncio

import jub.dto.v2 as DTO

import _domain as D
from _common import build_client, item_ids, require, save_state, unwrap


def tags_for(product: dict) -> list[str]:
    """All item ids of the catalogs listed in product['tag_catalogs']."""
    return [iid for key in product["tag_catalogs"] for iid in item_ids(key)]


async def main() -> None:
    client       = await build_client()
    obs_id       = require("observatory_id", "04_observatories.py")
    secondary_id = require("secondary_observatory_id", "04_observatories.py")
    require("items", "03_catalogs.py")

    first, *rest = D.PRODUCTS
    product_ids: dict[str, str] = {}

    # ── 1. One product: created, linked to `observatory_id` and tagged ────
    created = unwrap(
        await client.create_product(DTO.ProductCreateDTO(
            name             = first["name"],
            description      = first["description"],
            observatory_id   = obs_id,
            catalog_item_ids = tags_for(first),
        )),
        f"create product {first['key']}",
    )
    product_ids[first["key"]] = created.product_id
    print(f"✓ [create_product]       {first['key']:<18} → {created.product_id} ({len(tags_for(first))} tags)")

    # ── 2. The rest in a single request ──────────────────────────────────
    bulk = unwrap(
        await client.bulk_assign_products(obs_id, DTO.BulkProductsDTO(products=[
            DTO.BulkProductItemDTO(
                name             = p["name"],
                description      = p["description"],
                catalog_item_ids = tags_for(p),
            )
            for p in rest
        ])),
        "bulk assign products",
    )
    key_by_name = {p["name"]: p["key"] for p in rest}
    for created in bulk.products:
        product_ids[key_by_name[created.name]] = created.product_id
        print(f"✓ [bulk_assign_products] {key_by_name[created.name]:<18} → {created.product_id}")

    # ── 3. A product can appear in several observatories ─────────────────
    # "Mortalidad por Causa y Estado" includes cancer deaths, so the cancer
    # observatory shows it too — same product, no copy.
    unwrap(
        await client.link_product_to_observatory(secondary_id, DTO.LinkProductDTO(product_id=product_ids[first["key"]])),
        "link product to secondary observatory",
    )
    print(f"✓ [link_product_to_observatory] {first['key']} also → {secondary_id}")

    save_state(products=product_ids)

    # ── 4. List ──────────────────────────────────────────────────────────
    for oid in (obs_id, secondary_id):
        products = unwrap(await client.list_observatory_products(oid), f"list products of {oid}")
        print(f"\n{oid} ({len(products)} products)")
        for p in products:
            print(f"  {p.product_id}  {p.name}")


if __name__ == "__main__":
    asyncio.run(main())
