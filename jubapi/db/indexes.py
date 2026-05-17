from pymongo import ASCENDING, DESCENDING
from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all application indexes. Safe to call on every boot — MongoDB skips existing indexes."""

    # observatory_product_links
    opl = db["observatory_product_links"]
    await opl.create_index([("observatory_id", ASCENDING), ("product_id", ASCENDING)], name="idx_obs_prod_compound")
    await opl.create_index([("product_id", ASCENDING)], name="idx_opl_product_id")

    # product_catalogs_item_links
    pcil = db["product_catalogs_item_links"]
    await pcil.create_index([("product_id", ASCENDING)], name="idx_pcil_product_id")
    await pcil.create_index([("catalog_item_id", ASCENDING)], name="idx_pcil_catalog_item_id")
    await pcil.create_index([("product_id", ASCENDING), ("catalog_item_id", ASCENDING)], name="idx_pcil_prod_item_compound")

    # catalog_items
    ci = db["catalog_items"]
    await ci.create_index([("catalog_item_id", ASCENDING)], name="idx_ci_catalog_item_id")
    await ci.create_index([("value", ASCENDING)], name="idx_ci_value")
    await ci.create_index([("value_type", ASCENDING), ("temporal_value", ASCENDING)], name="idx_ci_temporal_compound")
    await ci.create_index([("catalog_type", ASCENDING)], name="idx_ci_catalog_type")

    # catalog_catalog_item_links
    ccil = db["catalog_catalog_item_links"]
    await ccil.create_index([("catalog_id", ASCENDING)], name="idx_ccil_catalog_id")
    await ccil.create_index([("catalog_item_id", ASCENDING)], name="idx_ccil_catalog_item_id")

    # catalog_item_relationships
    cir = db["catalog_item_relationships"]
    await cir.create_index([("parent_id", ASCENDING)], name="idx_cir_parent_id")
    await cir.create_index([("child_id", ASCENDING)], name="idx_cir_child_id")

    # catalog_item_aliases
    cia = db["catalog_item_aliases"]
    await cia.create_index([("value", ASCENDING)], name="idx_cia_value")
    await cia.create_index([("catalog_item_alias_id", ASCENDING)], name="idx_cia_alias_id")

    # catalog_item_catalog_alias_links
    cical = db["catalog_item_catalog_alias_links"]
    await cical.create_index([("catalog_item_alias_id", ASCENDING)], name="idx_cical_alias_id")
    await cical.create_index([("catalog_item_id", ASCENDING)], name="idx_cical_item_id")

    # products
    await db["products"].create_index([("product_id", ASCENDING)], name="idx_products_product_id")

    # data_records
    dr = db["data_records"]
    await dr.create_index([("source_id", ASCENDING)], name="idx_dr_source_id")
    await dr.create_index([("source_id", ASCENDING), ("spatial_id", ASCENDING)], name="idx_dr_source_spatial")

    # observatory_search_suggestions
    await db["observatory_search_suggestions"].create_index(
        [("observatory_id", ASCENDING), ("hit_count", DESCENDING)], name="idx_oss_obs_hits"
    )
