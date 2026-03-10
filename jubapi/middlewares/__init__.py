
import jubapi.services.v2 as S
import jubapi.repositories.v2 as R
import jubapi.db.constants as DC
from jubapi.db import get_collection


def get_search_service()->S.SearchService:
    # observatories_service = get_observatories_service()
    service = S.SearchService(
        catalog_alias_repository                   = R.CatalogItemAliasesRepository(get_collection(DC.CollectionNames.CATALOG_ITEM_ALIASES.value)),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(get_collection(DC.CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value)),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(get_collection(DC.CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value)),
        catalog_item_repository                    = R.CatalogItemsRepository(get_collection(DC.CollectionNames.CATALOG_ITEMS.value)),
        observatory_product_link_repository        = R.ObservatoryToProductLinkRepository(get_collection(DC.CollectionNames.OBSERVATORY_PRODUCT_LINKS.value)),
        product_repository                         = R.ProductsRepository(get_collection(DC.CollectionNames.PRODUCTS.value)),
        product_catalog_item_link_repository= R.ProductToCatalogItemLinkRepository(get_collection(DC.CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value)),
        observatory_catalog_link_repository= R.ObservatoryToCatalogLinkRepository(get_collection(DC.CollectionNames.OBSERVATORY_CATALOG_LINKS.value)),
        catalog_catalog_item_link_repository= R.CatalogToCatalogItemLinkRepository(get_collection(DC.CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value)),
        observatory_repository = R.ObservatoriesRepository(get_collection(DC.CollectionNames.OBSERVATORIES.value))

    )
    return service

def get_observatories_service()->S.ObservatoriesService:
    collection = get_collection(name=DC.CollectionNames.OBSERVATORIES.value)
    repository = R.ObservatoriesRepository(collection= collection)

    products_collection                        = get_collection(name=DC.CollectionNames.PRODUCTS.value)
    # catalog_collection                         = get_collection(name=DC.CollectionNames.CATALOGS.value)
    # catalog_items_collection                   = get_collection(name=DC.CollectionNames.CATALOG_ITEMS.value)
    # catalog_item_values_collection             = get_collection(name=DC.CollectionNames.CATALOG_ITEM_VALUES.value)
    observatory_to_product_link_collection     = get_collection(DC.CollectionNames.OBSERVATORY_PRODUCT_LINKS.value)
    product_catalog_item_link_collection       = get_collection(DC.CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value)
    catalog_item_relationship_collection       = get_collection(DC.CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value)
    catalog_catalogs_item_link_collection      = get_collection(DC.CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value)
    catalog_item_catalog_alias_link_collection = get_collection(DC.CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value)
    observatory_catalog_link_collection        = get_collection(DC.CollectionNames.OBSERVATORY_CATALOG_LINKS.value)

    product_repository                  = R.ProductsRepository(products_collection)
    # catalog_repository                  = R.CatalogRepository(catalog_collection)
    # catalog_item_repository             = R.CatalogItemRepository(catalog_items_collection)
    # catalog_item_value_repository       = R.CatalogItemAliasRepository(catalog_item_values_collection)
    observatory_product_link_repository = R.ObservatoryToProductLinkRepository(observatory_to_product_link_collection)
    
    # 2. Link Manager

    graph_link_manager = S.GraphLinkManager(
        observatory_product_link_repository        = observatory_product_link_repository,
        product_catalog_item_link_repository       = R.ProductToCatalogItemLinkRepository(product_catalog_item_link_collection),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(catalog_item_relationship_collection),
        catalog_catalog_item_link_repository       = R.CatalogToCatalogItemLinkRepository(catalog_catalogs_item_link_collection ),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(catalog_item_catalog_alias_link_collection),
        observatory_catalog_link_repository        = R.ObservatoryToCatalogLinkRepository(observatory_catalog_link_collection)
    )
    service    = S.ObservatoriesService(
        graph_link_manager                  = graph_link_manager,
        observatory_repository              = repository,
        observatory_product_link_repository = observatory_product_link_repository,
        product_repository                  = product_repository,
    )
    return service