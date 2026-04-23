
from typing import Optional,Annotated
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
import jubapi.services.v2 as S
import jubapi.repositories.v2 as R
import jubapi.db.constants as DC
from jubapi.db import get_collection
from jubapi.storage import StorageBackend, LocalStorageBackend
from xolo.client.client import XoloClient
import jubapi.dto.v2 as DTO
from jubapi.log import Log
import jubapi.config as Cfg
import jubapi.errors as EX

L = Log(
    name = __name__,
    path = Cfg.JUB_LOG_PATH
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_xolo_client() -> XoloClient:
    return XoloClient(
        api_url=Cfg.JUB_XOLO_API_URL,
        secret=Cfg.JUB_XOLO_SECRET,
        # hostname = Cfg.JUB_XOLO_HOSTNAME,
        # port     = Cfg.JUB_XOLO_PORT,
        # secret   = Cfg.JUB_XOLO_SECRET,
        # version  = Cfg.JUB_XOLO_VERSION
    )



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
        catalog_repository = R.CatalogsRepository(get_collection(DC.CollectionNames.CATALOGS.value)),
        data_records_repository= R.DataRecordsRepository(get_collection(DC.CollectionNames.DATA_RECORDS.value))

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


def get_notification_service()->S.NotificationService:
    collection = get_collection(name=DC.CollectionNames.NOTIFICATIONS.value)
    repository = R.NotificationsRepository(collection= collection)
    service    = S.NotificationService(
        repository= repository
    )
    return service

def get_user_profile_service()->S.UsersProfileXService:
    collection           = get_collection(name=DC.CollectionNames.USER_PROFILES.value)
    repository           = R.UserProfileXRepository(collection= collection)
    auth_service         = S.AuthenticationService()
    notification_service = S.NotificationService(repository=R.NotificationsRepository(get_collection(DC.CollectionNames.NOTIFICATIONS.value)))
    service = S.UsersProfileXService(
        user_profile_repository = repository,
        auth_service            = auth_service,
        notification_service    = notification_service
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


async def __get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    temporal_secret_key: Annotated[Optional[str], Header(alias="Temporal-Secret-Key")] = None,
    users_profiles_service: S.UsersProfileXService = Depends(get_user_profile_service),
    xolo_client: XoloClient = Depends(get_xolo_client)
):

    try:
        user_result =  xolo_client.get_current_user(
            token = token, 
            temporal_secret = temporal_secret_key
        )
        if user_result.is_err:
            e = user_result.unwrap_err() 
            L.error({
                "msg": f"Error getting user from Xolo: {e.detail.msg}",
                "code": e.code,
                "raw_error": e.detail.raw_error
            })
            raise EX.InvalidCredentialsError().to_http_exception()
        
        user_dto            = user_result.unwrap()
        user_profile_result = await users_profiles_service.get_user_profile_by_username(username = user_dto.username)
        # print("User profile result:", user_profile_result)
        if user_profile_result.is_err:
            e = user_profile_result.unwrap_err()
            L.error({
                "msg": f"Error getting user profile: {e.detail}",
            })
            raise EX.InvalidCredentialsError().to_http_exception()
        user_profile    = user_profile_result.unwrap()

        return DTO.UserProfileDTO(
            username   = user_profile.username,
            user_id    = user_profile.user_id,
            email      = user_profile.email,
            is_disabled= user_profile.disabled,
            first_name = user_profile.first_name,
            last_name  = user_profile.last_name,
            fullname   = user_profile.fullname,
            settings   = DTO.UserPreferencesDTO.from_model(user_profile.settings),
            created_at = user_profile.created_at.isoformat(),
            updated_at = user_profile.updated_at.isoformat(),
        )
        # user_profile = 

    except Exception as e:
        L.error(f"Error in __get_current_user: {str(e)}")
        raise EX.InvalidCredentialsError().to_http_exception()

async def get_current_user(
    current_user: Annotated[DTO.UserProfileDTO, Depends(__get_current_user)]
):
    if current_user.is_disabled:
        raise EX.AuthorizationError(
            detail=f"User {current_user.user_id} is disabled."
        )
    return current_user


def get_tasks_repository()->R.TaskRepository:
    repository = R.TaskRepository(get_collection(DC.CollectionNames.TASKS.value))
    return repository

def get_tasks_service(
    notification_service: S.NotificationService = Depends(get_notification_service),
    repository: R.TaskRepository = Depends(get_tasks_repository)
)->S.TasksService:
    service = S.TasksService(
        repository=repository,
        notification_service=notification_service
    )
    return service


def get_data_ingestion_service() -> S.DataIngestionService:
    return S.DataIngestionService(
        source_repo = R.DataSourceRepository(get_collection(DC.CollectionNames.DATA_SOURCES.value)),
        record_repo = R.DataRecordsRepository(get_collection(DC.CollectionNames.DATA_RECORDS.value)),
    )


def get_data_query_service() -> S.DataQueryService:
    return S.DataQueryService(
        record_repo               = R.DataRecordsRepository(get_collection(DC.CollectionNames.DATA_RECORDS.value)),
        catalog_item_repo         = R.CatalogItemsRepository(get_collection(DC.CollectionNames.CATALOG_ITEMS.value)),
        catalog_alias_repo        = R.CatalogItemAliasesRepository(get_collection(DC.CollectionNames.CATALOG_ITEM_ALIASES.value)),
        catalog_item_alias_link_repo = R.CatalogItemToCatalogAliasLinkRepository(get_collection(DC.CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value)),
    )


# Storage backend — swap LocalStorageBackend for a cloud implementation in production
_storage_backend: StorageBackend = LocalStorageBackend()

def get_storage_backend() -> StorageBackend:
    return _storage_backend