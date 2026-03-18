
from fastapi import Depends
import jubapi.services.v2 as S
import jubapi.repositories.v2 as R
import jubapi.db.constants as DC
from jubapi.db import get_collection

def get_link_manager()->S.GraphLinkManager:
    graph_link_manager = S.GraphLinkManager(
        observatory_product_link_repository        = R.ObservatoryToProductLinkRepository(get_collection(DC.CollectionNames.OBSERVATORY_PRODUCT_LINKS.value)),
        observatory_catalog_link_repository        = R.ObservatoryToCatalogLinkRepository(get_collection(DC.CollectionNames.OBSERVATORY_CATALOG_LINKS.value)),
        catalog_catalog_item_link_repository       = R.CatalogToCatalogItemLinkRepository(get_collection(DC.CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value)),
        product_catalog_item_link_repository       = R.ProductToCatalogItemLinkRepository(get_collection(DC.CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value)),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(get_collection(DC.CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value)),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(get_collection(DC.CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value)),
    )
    return graph_link_manager



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
        observatory_repository = R.ObservatoriesRepository(get_collection(DC.CollectionNames.OBSERVATORIES.value)),
        catalog_repository = R.CatalogsRepository(get_collection(DC.CollectionNames.CATALOGS.value))

    )
    return service



def get_catalog_service(link_manager: S.GraphLinkManager=Depends(get_link_manager))->S.CatalogService:
    collection = get_collection(name=DC.CollectionNames.CATALOGS.value)
    repository = R.CatalogsRepository(collection= collection)

    catalog_item_collection                   = get_collection(name=DC.CollectionNames.CATALOG_ITEMS.value)
    catalog_item_repository                   = R.CatalogItemsRepository(catalog_item_collection)
    catalog_item_alias_collection             = get_collection(name=DC.CollectionNames.CATALOG_ITEM_ALIASES.value)
    catalog_item_alias_repository             = R.CatalogItemAliasesRepository(catalog_item_alias_collection)


    service = S.CatalogService(
        catalog_repository            = repository,
        catalog_item_alias_repository = catalog_item_alias_repository,
        catalog_items_repository      = catalog_item_repository,
        link_manager                  = link_manager
    )
    return service



def get_product_service(link_manager: S.GraphLinkManager=Depends(get_link_manager))->S.ProductService:
    collection = get_collection(name=DC.CollectionNames.PRODUCTS.value)
    repository = R.ProductsRepository(collection= collection)
    service = S.ProductService(
        product_repository = repository,
        link_manager       = link_manager
    )
    return service


def get_observatories_service(graph_link_manager: S.GraphLinkManager=Depends(get_link_manager))->S.ObservatoriesService:
    collection                             = get_collection(name=DC.CollectionNames.OBSERVATORIES.value)
    repository                             = R.ObservatoriesRepository(collection= collection)
    products_collection                    = get_collection(name=DC.CollectionNames.PRODUCTS.value)
    observatory_to_product_link_collection = get_collection(DC.CollectionNames.OBSERVATORY_PRODUCT_LINKS.value)
    product_repository                     = R.ProductsRepository(products_collection)
    observatory_product_link_repository    = R.ObservatoryToProductLinkRepository(observatory_to_product_link_collection)
    service                                = S.ObservatoriesService(
        graph_link_manager                  = graph_link_manager,
        observatory_repository              = repository,
        observatory_product_link_repository = observatory_product_link_repository,
        product_repository                  = product_repository,
    )
    return service