from pymongo.results import UpdateResult,DeleteResult
from typing import List,Optional,Tuple,Dict,Any
import jubapi.models.v2 as M
import asyncio
import jubapi.repositories.v2 as R
import jubapi.dto.v2 as DTO
from jubapi.querylang.v2.parser  import QueryAST,Condition,ConditionOperators
from jubapi.log.log import Log
import jubapi.errors as EX
from jubapi.db import CollectionNames

from option import Result,Ok,Err
import os
import datetime as DT

log = Log(
    name = __name__,
    path = os.environ.get("JUB_LOG_PATH", "/log"),
)

class GraphLinkManager:
    """
    Centralized manager for severing edges in the Jub graph.
    Relies strictly on injected Link Repositories.
    """
    def __init__(
        self, 
        observatory_product_link_repository: R.ObservatoryToProductLinkRepository,
        observatory_catalog_link_repository: R.ObservatoryToCatalogLinkRepository,
        catalog_catalog_item_link_repository: R.CatalogToCatalogItemLinkRepository,
        product_catalog_item_link_repository: R.ProductToCatalogItemLinkRepository,
        catalog_item_relationship_repository: R.CatalogItemRelationshipRepository,
        catalog_item_catalog_alias_link_repository: R.CatalogItemToCatalogAliasLinkRepository
    ):
        self.observatory_product_link_repository        = observatory_product_link_repository
        self.observatory_catalog_link_repository        = observatory_catalog_link_repository
        self.catalog_catalog_item_link_repository               = catalog_catalog_item_link_repository
        self.product_catalog_item_link_repository       = product_catalog_item_link_repository
        self.catalog_item_relationship_repository       = catalog_item_relationship_repository
        self.catalog_item_catalog_alias_link_repository = catalog_item_catalog_alias_link_repository

    # Get links
    async def get_products_linked_to_observatory(self, observatory_id: str) -> Result[List[str], EX.JubError]:
        try:
            cursor = self.observatory_product_link_repository.collection.find({"observatory_id": observatory_id})
            results = await cursor.to_list(length=None)
            product_ids = [doc["product_id"] for doc in results]
            return Ok(product_ids)
        except Exception as e:
            log.error(f"Error getting products linked to observatory: {e}")
            return Err(EX.JubError.from_exception(e))

    async def count_products_linked_to_observatory(self, observatory_id: str) -> Result[int, EX.JubError]:
        try:
            count = await self.observatory_product_link_repository.collection.count_documents({"observatory_id": observatory_id})
            return Ok(count)
        except Exception as e:
            log.error(f"Error counting products linked to observatory: {e}")
            return Err(EX.JubError.from_exception(e))
        
    async def exists_product_linked_to_observatory(self, observatory_id: str, product_id:str) -> Result[bool, EX.JubError]:
        try:
            count = await self.observatory_product_link_repository.collection.count_documents({"observatory_id": observatory_id, "product_id": product_id})
            return Ok(count > 0)
        except Exception as e:
            log.error(f"Error checking existence of product linked to observatory: {e}")
            return Err(EX.JubError.from_exception(e))
        
    async def exists_products_linked_to_observatory(self, observatory_id: str) -> Result[bool, EX.JubError]:
        try:
            count = await self.observatory_product_link_repository.collection.count_documents({"observatory_id": observatory_id})
            return Ok(count > 0)
        except Exception as e:
            log.error(f"Error checking existence of products linked to observatory: {e}")
            return Err(EX.JubError.from_exception(e))
    
    # _______________________
    async def get_catalogs_linked_to_observatory(self, observatory_id: str) -> Result[List[str], EX.JubError]:
        try:
            cursor = self.observatory_catalog_link_repository.collection.find({"observatory_id": observatory_id})
            results = await cursor.to_list(length=None)
            catalog_ids = [doc["catalog_id"] for doc in results]
            return Ok(catalog_ids)
        except Exception as e:
            log.error(f"Error getting catalogs linked to observatory: {e}")
            return Err(EX.JubError.from_exception(e))
    async def count_catalogs_linked_to_observatory(self, observatory_id: str) -> Result[int, EX.JubError]:
        try:
            count = await self.observatory_catalog_link_repository.collection.count_documents({"observatory_id": observatory_id})
            return Ok(count)
        except Exception as e:
            log.error(f"Error counting catalogs linked to observatory: {e}")
            return Err(EX.JubError.from_exception(e))
    async def exists_catalog_linked_to_observatory(self, observatory_id: str, catalog_id:str) -> Result[bool, EX.JubError]:
        try:
            count = await self.observatory_catalog_link_repository.collection.count_documents({"observatory_id": observatory_id, "catalog_id": catalog_id})
            return Ok(count > 0)
        except Exception as e:
            log.error(f"Error checking existence of catalog linked to observatory: {e}")
            return Err(EX.JubError.from_exception(e))
    async def exists_catalogs_linked_to_observatory(self, observatory_id: str) -> Result[bool, EX.JubError]:
        try:
            count = await self.observatory_catalog_link_repository.collection.count_documents({"observatory_id": observatory_id})
            return Ok(count > 0)
        except Exception as e:
            log.error(f"Error checking existence of catalogs linked to observatory: {e}")
            return Err(EX.JubError.from_exception(e))
    # _______________________
    async def get_catalog_items_linked_to_catalog(self, catalog_id: str) -> Result[List[str], EX.JubError]:
        try:
            cursor = self.catalog_catalog_item_link_repository.collection.find({"catalog_id": catalog_id})
            results = await cursor.to_list(length=None)
            catalog_item_ids = [doc["catalog_item_id"] for doc in results]
            return Ok(catalog_item_ids)
        except Exception as e:
            log.error(f"Error getting catalog items linked to catalog: {e}")
            return Err(EX.JubError.from_exception(e))
    async def count_catalog_items_linked_to_catalog(self, catalog_id: str) -> Result[int, EX.JubError]:
        try:
            count = await self.catalog_catalog_item_link_repository.collection.count_documents({"catalog_id": catalog_id})
            return Ok(count)
        except Exception as e:
            log.error(f"Error counting catalog items linked to catalog: {e}")
            return Err(EX.JubError.from_exception(e))
    async def exists_catalog_item_linked_to_catalog(self, catalog_id: str, catalog_item_id:str) -> Result[bool, EX.JubError]:
        try:
            count = await self.catalog_catalog_item_link_repository.collection.count_documents({"catalog_id": catalog_id, "catalog_item_id": catalog_item_id})
            return Ok(count > 0)
        except Exception as e:
            log.error(f"Error checking existence of catalog item linked to catalog: {e}")
            return Err(EX.JubError.from_exception(e))
    async def exists_catalog_items_linked_to_catalog(self, catalog_id: str) -> Result[bool, EX.JubError]:
        try:
            count = await self.catalog_catalog_item_link_repository.collection.count_documents({"catalog_id": catalog_id})
            return Ok(count > 0)
        except Exception as e:
            log.error(f"Error checking existence of catalog items linked to catalog: {e}")
            return Err(EX.JubError.from_exception(e))
    # _______________________
    async def get_catalog_items_linked_to_product(self, product_id: str) -> Result[List[str], EX.JubError]:
        try:
            cursor = self.product_catalog_item_link_repository.collection.find({"product_id": product_id})
            results = await cursor.to_list(length=None)
            catalog_item_ids = [doc["catalog_item_id"] for doc in results]
            return Ok(catalog_item_ids)
        except Exception as e:
            log.error(f"Error getting catalog items linked to product: {e}")
            return Err(EX.JubError.from_exception(e))
    async def count_catalog_items_linked_to_product(self, product_id: str) -> Result[int, EX.JubError]:
        try:
            count = await self.product_catalog_item_link_repository.collection.count_documents({"product_id": product_id})
            return Ok(count)
        except Exception as e:
            log.error(f"Error counting catalog items linked to product: {e}")
            return Err(EX.JubError.from_exception(e))
    async def exists_catalog_item_linked_to_product(self, product_id: str, catalog_item_id:str) -> Result[bool, EX.JubError]:
        try:
            count = await self.product_catalog_item_link_repository.collection.count_documents({"product_id": product_id, "catalog_item_id": catalog_item_id})
            return Ok(count > 0)
        except Exception as e:
            log.error(f"Error checking existence of catalog item linked to product: {e}")
            return Err(EX.JubError.from_exception(e))
    async def exists_catalog_items_linked_to_product(self, product_id: str) -> Result[bool, EX.JubError]:
        try:
            count = await self.product_catalog_item_link_repository.collection.count_documents({"product_id": product_id})
            return Ok(count > 0)
        except Exception as e:
            log.error(f"Error checking existence of catalog items linked to product: {e}")
            return Err(EX.JubError.from_exception(e))
    # _______________________


    async def link_observatory_to_product(self, observatory_id: str, product_id: str)->Result[UpdateResult,EX.JubError]:
        try:
            link = M.ObservatoryToProductLink(observatory_id=observatory_id, product_id=product_id)
            r = await self.observatory_product_link_repository.collection.update_one(
                {"observatory_id": observatory_id, "product_id": product_id},
                {"$set": link.model_dump()},
                upsert=True
            )
            return Ok(r)
        except Exception as e:
            log.error(f"Error linking observatory to product: {e}")
            return Err(EX.JubError.from_exception(e))
            # raise EX.JubError(f"Failed to link observatory to product: {str(e)}")

    async def link_observatory_to_catalog(self, observatory_id: str, catalog_id: str,level:int=0)->Result[UpdateResult,EX.JubError]:
        try:
            link = M.ObservatoryToCatalogLink(observatory_id=observatory_id, catalog_id=catalog_id,level=level)
            r = await self.observatory_catalog_link_repository.collection.update_one(
                {"observatory_id": observatory_id, "catalog_id": catalog_id},
                {"$set": link.model_dump()},
                upsert=True
            )
            return Ok(r)
        except Exception as e:
            log.error(f"Error linking observatory to catalog: {e}")
            return Err(EX.JubError.from_exception(e))
        

    async def link_catalog_to_item(self, catalog_id: str, catalog_item_id: str)->Result[UpdateResult,EX.JubError]:
        try:
            link = M.CatalogToCatalogItemLink(catalog_id=catalog_id, catalog_item_id=catalog_item_id)
            r = await self.catalog_catalog_item_link_repository.collection.update_one(
                {"catalog_id": catalog_id, "catalog_item_id": catalog_item_id},
                {"$set": link.model_dump()},
                upsert=True
            )
            return Ok(r)
        except Exception as e:
            log.error(f"Error linking catalog to item: {e}")
            return Err(EX.JubError.from_exception(e))
        

    async def link_product_to_catalog_item(self, product_id: str, catalog_item_id: str)->Result[UpdateResult,EX.JubError]:
        """Tags a product with a specific dimension (e.g., 'FEMALE' or 'VIC')."""
        try:
            link = M.CatalogItemToProductLink(product_id=product_id, catalog_item_id=catalog_item_id)
            r = await self.product_catalog_item_link_repository.collection.update_one(
                {"product_id": product_id, "catalog_item_id": catalog_item_id},
                {"$set": link.model_dump()},
                upsert=True
            )
            return Ok(r)
        except Exception as e:
            log.error(f"Error linking product to catalog item: {e}")
            return Err(EX.JubError.from_exception(e))
        

    async def set_item_relationship(self, parent_id: str, child_id: str)->Result[UpdateResult,EX.JubError]:
        """Builds the hierarchy (e.g., MX -> TAM)."""
        try:
            link = M.CatalogItemRelationship(parent_id=parent_id, child_id=child_id)
            r = await self.catalog_item_relationship_repository.collection.update_one(
                {"parent_id": parent_id, "child_id": child_id},
                {"$set": link.model_dump()},
                upsert=True
            )
            return Ok(r)
        except Exception as e:
            log.error(f"Error setting item relationship: {e}")
            return Err(EX.JubError.from_exception(e))

    async def link_item_to_alias(self, catalog_item_id: str, catalog_item_alias_id: str)->Result[UpdateResult,EX.JubError]:
        """Links an alias/value to the canonical item."""
        try:

            link = M.CatalogItemToCatalogAliasLink(
                catalog_item_id=catalog_item_id, 
                catalog_item_alias_id=catalog_item_alias_id
            )
            r = await self.catalog_item_catalog_alias_link_repository.collection.update_one(
                {"catalog_item_id": catalog_item_id, "catalog_item_value_id": catalog_item_alias_id},
                {"$set": link.model_dump()},
                upsert=True
            )
            return Ok(r)
        except Exception as e:
            log.error(f"Error linking item to value: {e}")
            return Err(EX.JubError.from_exception(e))

    #  Remove links (called by services when an entity is deleted, to maintain graph integrity)
    async def remove_all_product_links(self, product_id: str)->Result[Tuple[DeleteResult, DeleteResult],EX.JubError]:
        """Called by ProductService when a product is completely deleted."""
        try:
            r1 = await self.observatory_product_link_repository.collection.delete_many({"product_id": product_id})
            r2 = await self.product_catalog_item_link_repository.collection.delete_many({"product_id": product_id})
            return Ok((r1, r2))
        except Exception as e:
            log.error(f"Error removing all product links: {e}")
            return Err(EX.JubError.from_exception(e))


    async def remove_all_catalog_links(self, catalog_id: str)->Result[Tuple[DeleteResult, DeleteResult],EX.JubError]:
        """Called by CatalogService when a catalog is completely deleted."""
        try:
            r1 = await self.observatory_catalog_link_repository.collection.delete_many({"catalog_id": catalog_id})
            r2 = await self.catalog_catalog_item_link_repository.collection.delete_many({"catalog_id": catalog_id})
            return Ok((r1, r2))
        except Exception as e:
            log.error(f"Error removing all catalog links: {e}")
            return Err(EX.JubError.from_exception(e))

    async def remove_all_catalog_item_links(self, catalog_item_id: str)->Result[Tuple[DeleteResult, DeleteResult, DeleteResult, DeleteResult],EX.JubError]:
        """
        Called by CatalogService when an item is deleted. 
        Wipes its tags, its aliases, and its parent/child relationships.
        """
        try:
            r1 = await self.catalog_catalog_item_link_repository.collection.delete_many({"catalog_item_id": catalog_item_id})
            r2 = await self.product_catalog_item_link_repository.collection.delete_many({"catalog_item_id": catalog_item_id})
            r3 = await self.catalog_item_catalog_alias_link_repository.collection.delete_many({"catalog_item_id": catalog_item_id})
            
            # Remove it from the hierarchy tree (whether it was a parent or a child)
            r4 = await self.catalog_item_relationship_repository.collection.delete_many({"$or": [
                {"parent_id": catalog_item_id},
                {"child_id": catalog_item_id}
            ]})
            return Ok((r1, r2, r3, r4))
        except Exception as e:
            log.error(f"Error removing all catalog item links: {e}")
            return Err(EX.JubError.from_exception(e))

    
class ObservatoriesService:
    def __init__(
        self, 
        observatory_repository: R.ObservatoriesRepository, 
        observatory_product_link_repository: R.ObservatoryToProductLinkRepository,
        product_repository: R.ProductsRepository,
        graph_link_manager: GraphLinkManager
    ):
        self.observatory_repository = observatory_repository
        self.observatory_product_link_repository = observatory_product_link_repository
        self.product_repository = product_repository
        self.graph_link_manager = graph_link_manager

    # --- Create Operations ---

    async def create_observatory(self, observatory: M.ObservatoryX) -> Result[str, EX.JubError]:
        exists_result = await self.observatory_repository.get_by_id(observatory.observatory_id)
        if exists_result.is_ok:
            return Err(EX.JubError(f"Observatory with ID {observatory.observatory_id} already exists"))
        
        return await self.observatory_repository.insert(observatory)

    async def add_catalog(self, observatory_id: str, catalog_id: str,level:int = 0) -> Result[bool, EX.JubError]:
        """Assigns an existing catalog to this observatory (e.g., SPATIAL or CIE10)."""
        result = await self.graph_link_manager.link_observatory_to_catalog(observatory_id, catalog_id,level)
        if result.is_err:
            log.error(f"Failed to link catalog {catalog_id} to observatory {observatory_id}: {result.unwrap_err()}")
            return Err(EX.JubError(f"Failed to link catalog {catalog_id} to observatory {observatory_id}: {result.unwrap_err()}"))
        return Ok(True)
    # --- Read Operations (Aggregation) ---

    async def get_observatories(self,query:Dict[str,Any]={},page_index:int=0, limit:int=10)-> Result[List[DTO.ObservatoryXDTO],EX.JubError]:
        """Fetches all observatories, optionally filtered by a query, and paginated."""
        try:
            cursor        = self.observatory_repository.collection.find(query).skip(page_index*limit).limit(limit)
            observatories = [DTO.ObservatoryXDTO.from_model(M.ObservatoryX.from_doc(doc)) for doc in await cursor.to_list(length=None)]
            return Ok(observatories)
        except Exception as e:
            log.error(f"Error fetching observatories: {e}")
            return Err(EX.JubError.from_exception(e))
        
    async def get_observatory(self, observatory_id: str) -> Result[DTO.ObservatoryXDTO, EX.JubError]:
        model = await self.observatory_repository.get_by_id(observatory_id) 
        if model.is_err:
            log.error(f"Error fetching observatory {observatory_id}: {model.unwrap_err()}")
            return Err(EX.JubError.from_exception(model.unwrap_err()))
        
        return Ok(DTO.ObservatoryXDTO.from_model(model.unwrap()))

    async def get_all_products_in_observatory(self, observatory_id: str) -> Result[List[M.ProductX], EX.JubError]:
        """
        Dynamically builds a $lookup pipeline to fetch all products for this domain.
        """
        pipeline = [
            {"$match": {"observatory_id": observatory_id}},
            {"$lookup": {
                "from": self.product_repository.collection.name, # Dynamic collection name
                "localField": "product_id",
                "foreignField": "product_id",
                "as": "product_data"
            }},
            {"$unwind": "$product_data"},
            {"$replaceRoot": {"newRoot": "$product_data"}}
        ]
        
        cursor = self.observatory_product_link_repository.collection.aggregate(pipeline)
        try:
            return Ok([M.ProductX(**doc) for doc in cursor])
        except Exception as e:
            log.error(f"Error fetching products in observatory: {e}")
            return Err(EX.UnknownError(str(e)))

    async def get_catalogs_by_observatory_id(self, observatory_id: str) -> Result[List[M.CatalogX], EX.JubError]:
        """
        Dynamically builds a $lookup pipeline to fetch all catalogs assigned to this domain.
        Executes asynchronously using motor.
        """
        try:
            print("BEFORE_PIPELINE")
            pipeline = [
                # 1. Find all link documents for this specific observatory
                {"$match": {"observatory_id": observatory_id}},
                
                # 2. Join the actual catalog documents
                {"$lookup": {
                    "from": CollectionNames.CATALOGS.value, # Dynamic collection name
                    "localField": "catalog_id",
                    "foreignField": "catalog_id",
                    "as": "catalog_data"
                }},
                
                # 3. Flatten the array created by $lookup
                {"$unwind": "$catalog_data"},
                
                # 4. Replace the root link document with the actual catalog metadata
                {"$replaceRoot": {"newRoot": "$catalog_data"}}
            ]
            
            # Execute against the linking collection
            cursor = self.graph_link_manager.observatory_catalog_link_repository.collection.aggregate(pipeline)
            documents = await cursor.to_list(length=None)
            
            # Parse into Pydantic models
            catalogs = [M.CatalogX(**doc) for doc in documents]
            return Ok(catalogs)
            
        except Exception as e:
            log.error({
                "message": "Error fetching catalogs for observatory",
                "error": str(e),
                "observatory_id": observatory_id
            })
            return Err(EX.JubError.from_exception(e)) 
    


    # --- Delete Operations ---

    async def delete_observatory(self, observatory_id: str) -> Result[bool, EX.JubError]:
        """Deletes the observatory (products remain in the database, just unassigned to this view)."""
        success = await self.observatory_repository.delete(observatory_id)
        return success

class CatalogService:
    def __init__(
        self, 
        catalog_repository: R.CatalogsRepository, 
        catalog_items_repository: R.CatalogItemsRepository,
        catalog_item_alias_repository: R.CatalogItemAliasesRepository, # The alias/value repo
        link_manager: GraphLinkManager
    ):
        self.catalog_repository            = catalog_repository
        self.catalog_item_repository       = catalog_items_repository
        self.catalog_item_alias_repository = catalog_item_alias_repository
        self.link_manager                  = link_manager

    # --- Create Operations ---

    async def create_catalog(self, catalog: M.CatalogX) -> Result[str,EX.JubError]:
        exists_result = await self.catalog_repository.get_by_id(catalog.catalog_id)
        if exists_result.is_ok:
            return Err(EX.AlreadyExists(f"Catalog with ID {catalog.catalog_id} already exists"))
        return await self.catalog_repository.insert(catalog)

    async def add_item_to_catalog(self, catalog_id: str, item: M.CatalogItemX, parent_id: Optional[str] = None) -> Result[str,EX.JubError]:
        """Saves a new item, links it to its catalog, and builds the hierarchy if requested."""
        insert_rest = await self.catalog_item_repository.insert(item)

        if insert_rest.is_err:
            log.error({
                "message": "Failed to insert catalog item",
                "error": insert_rest.unwrap_err(),
                "catalog_id": catalog_id,
            })
            return Err(EX.JubError(f"Failed to insert catalog item: {insert_rest.unwrap_err()}"))
        
        item_id = insert_rest.unwrap()
        
        # Link to the main catalog (e.g., SPATIAL)
        result = await self.link_manager.link_catalog_to_item(catalog_id, item_id)
        if result.is_err:
            # Rollback item insertion if linking fails
            delete_catalog_item_result = await self.catalog_item_repository.delete(item_id)

            if delete_catalog_item_result.is_err:
                log.error(f"Failed to rollback catalog item after link failure: {delete_catalog_item_result.unwrap_err()}")
                return Err(EX.JubError(f"Failed to rollback catalog item after link failure: {delete_catalog_item_result.unwrap_err()}"))

            return Err(EX.JubError(f"Failed to link item to catalog: {result.unwrap_err()}"))
        
        # Link to parent if it exists (e.g., TAM -> VIC)
        if parent_id:
            await self.link_manager.set_item_relationship(parent_id, item_id)
            
        return Ok(item_id)

    async def add_value_to_item(self, catalog_item_id: str, value: M.CatalogItemAlias) -> Result[str,EX.JubError]:
        """Saves an alias (e.g., '1' or 'CDVALLES') and links it to the canonical item."""
        try: 
            val_id_result = await self.catalog_item_alias_repository.insert(value)
            if val_id_result.is_err:
                log.error(f"Failed to insert catalog item alias: {val_id_result.unwrap_err()}")
                return Err(EX.JubError(f"Failed to insert catalog item alias: {val_id_result.unwrap_err()}"))
            
            val_id = val_id_result.unwrap()
            
            res = await self.link_manager.link_item_to_alias(catalog_item_id, val_id)
            if res.is_err:
                # Rollback alias insertion if linking fails
                delete_alias_result = await self.catalog_item_alias_repository.delete(val_id)

                if delete_alias_result.is_err:
                    log.error(f"Failed to rollback catalog item alias after link failure: {delete_alias_result.unwrap_err()}")
                    return Err(EX.JubError(f"Failed to rollback catalog item alias after link failure: {delete_alias_result.unwrap_err()}"))

                return Err(EX.JubError(f"Failed to link alias to catalog item: {res.unwrap_err()}"))
            return Ok(val_id)
        except Exception as e:
            log.error(f"Error adding value to item: {e}")
            return Err(EX.JubError.from_exception(e))
    
    async def get_catalog_hierarchy_levels(self, root_catalog_id: str) -> Result[List[M.CatalogX], EX.JubError]:
        """
        Gets the structural hierarchy for a SPECIFIC catalog family.
        Example: Pass "cat_cie10", get [Capítulo, Bloque, Categoría] in exact order.
        Example: Pass "cat_spatial_mx", get [País, Estado, Municipio] in exact order.
        """
        try:
            # We instantly grab the whole family and sort by level (0, 1, 2, 3...)
            cursor = self.catalog_repository.collection.find(
                {"root_catalog_id": root_catalog_id}
            ).sort("level", 1)
            
            docs = await cursor.to_list(length=None)
            return Ok([M.CatalogX(**doc) for doc in docs])
            
        except Exception as e:
            return Err(EX.JubError.from_exception(e))

    async def get_items_by_parent(self, parent_item_id: str) -> Result[List[M.CatalogItemX], EX.JubError]:
        """
        Gets the specific sub-level items.
        Example: Pass "MX" (Mexico), get all States linked to it.
        """
        try:
            # 1. Find all children edges in the relationship collection
            rel_cursor = self.link_manager.catalog_item_relationship_repository.collection.find({"parent_id": parent_item_id})
            rel_docs = await rel_cursor.to_list(length=None)
            
            if not rel_docs:
                return Ok([])
                
            child_ids = [doc["child_id"] for doc in rel_docs]
            
            # 2. Fetch the actual CatalogItem metadata for those children
            item_cursor = self.catalog_item_repository.collection.find({"catalog_item_id": {"$in": child_ids}})
            item_docs = await item_cursor.to_list(length=None)
            
            items = [M.CatalogItemX(**doc) for doc in item_docs]
            items.sort(key=lambda x: x.name) # Alphabetical for the UI
            
            return Ok(items)
        except Exception as e:
            return Err(EX.JubError.from_exception(e))
    # --- Delete Operations (Cascading) ---

    async def delete_catalog_item(self, catalog_item_id: str) -> Result[bool, EX.JubError]:
        """Deletes an item and securely wipes its tags, aliases, and hierarchy edges."""
        try:
            success = await self.catalog_item_repository.delete(catalog_item_id)
            if success:
                await self.link_manager.remove_all_catalog_item_links(catalog_item_id)
            return Ok(success)
        except Exception as e:
            return Err(EX.JubError.from_exception(e))

    async def delete_catalog(self, catalog_id: str) -> Result[bool, EX.JubError]:
        """Deletes a catalog and its direct links."""
        try:
            result = await self.catalog_repository.delete(catalog_id)
            if result.is_ok:
                await self.link_manager.remove_all_catalog_links(catalog_id)
                return Ok(result.unwrap())
            
            return result
        except Exception as e:
            return Err(EX.JubError.from_exception(e))


    
class ProductService:
    def __init__(
        self, 
        product_repository: R.ProductsRepository, 
        link_manager: GraphLinkManager
    ):
        self.product_repository = product_repository
        self.link_manager = link_manager

    
    async def get_product_by_id(self, product_id: str) -> Result[M.ProductX, EX.JubError]:
        """Fetches a product by its ID, including all its tags."""
        try:
            product_res = await self.product_repository.get_by_id(product_id)
            if product_res.is_err:
                log.error({
                    "message": f"Failed to fetch product {product_id}",
                    "error": str(product_res.unwrap_err())
                })
                return product_res
            
            product = product_res.unwrap()
            
            # # Fetch tags
            # tags_res = await self.link_manager.get_catalog_items_linked_to_product(product_id)
            # if tags_res.is_err:
            #     log.warning({
            #         "message": f"Failed to fetch tags for product {product_id}",
            #         "error": tags_res.unwrap_err()
            #     })
            #     product.tags = []
            # else:
            #     product.tags = tags_res.unwrap()
            
            return Ok(product)
        except Exception as e:
            log.error({
                "message": f"Error fetching product by ID: {product_id}",
                "error": str(e)
            })
            return Err(EX.JubError.from_exception(e))

    async def insert_product(
        self, 
        product: M.ProductX, 
        observatory_id: str, 
        catalog_item_ids: List[str] = None
    ) -> Result[str, EX.JubError]:
        """Inserts a dataset, assigns it to an observatory, and applies all its tags."""
        
        # 1. Save the product
        prod_res = await self.product_repository.insert(product)
        if prod_res.is_err:
            return prod_res

        # 2. Assign to the observatory
        obs_link_res = await self.link_manager.link_observatory_to_product(observatory_id, product.product_id)
        if obs_link_res.is_err:
            return obs_link_res

        # 3. Apply the tags
        if catalog_item_ids:
            for item_id in catalog_item_ids:
                tag_res = await self.link_manager.link_product_to_catalog_item(product.product_id, item_id)
                if tag_res.is_err:
                    log.warning({
                        "message": f"Failed to tag product {product.product_id} with {item_id}",
                        "error": tag_res.unwrap_err()
                    })
                    # Depending on your strictness, you could return an Err here, 
                    # but usually, you want to keep going even if one tag fails.

        return Ok(product.product_id)

    async def delete_product(self, product_id: str) -> Result[bool, EX.JubError]:
        """Deletes the product and securely wipes its observatory assignment and tags."""
        del_res = await self.product_repository.delete(product_id)
        if del_res.is_err:
            return del_res
            
        wipe_res = await self.link_manager.remove_all_product_links(product_id)
        if wipe_res.is_err:
            return wipe_res
            
        return Ok(True)


class SearchService:
    def __init__(
        self, 
        observatory_product_link_repository:R.ObservatoryToProductLinkRepository,
        product_catalog_item_link_repository: R.ProductToCatalogItemLinkRepository,
        catalog_item_relationship_repository: R.CatalogItemRelationshipRepository,
        catalog_item_repository: R.CatalogItemsRepository,
        product_repository: R.ProductsRepository,
        catalog_alias_repository: R.CatalogItemAliasesRepository,
        catalog_item_catalog_alias_link_repository: R.CatalogItemToCatalogAliasLinkRepository,
        observatory_catalog_link_repository: R.ObservatoryToCatalogLinkRepository,
        catalog_catalog_item_link_repository: R.CatalogToCatalogItemLinkRepository,
        observatory_repository: R.ObservatoriesRepository
    ):
        self.observatory_product_link_repository  = observatory_product_link_repository
        self.product_catalog_item_link_repository = product_catalog_item_link_repository
        self.catalog_item_relationship_repository = catalog_item_relationship_repository
        self.catalog_item_repository              = catalog_item_repository
        self.product_repository                   = product_repository
        self.catalog_alias_repository             = catalog_alias_repository
        self.catalog_item_catalog_alias_link_repository = catalog_item_catalog_alias_link_repository
        self.observatory_catalog_link_repository = observatory_catalog_link_repository
        self.catalog_catalog_item_link_repository = catalog_catalog_item_link_repository
        self.observatory_repository              = observatory_repository
        
 

    async def search_observatories(self,query:str)->Result[DTO.ObservatoryXDTO, EX.JubError]:
        """
        Finds all observatories that possess the required catalogs to satisfy the DSL query.
        """
        try:
            # 1. Parse the DSL into your AST
            ast                  = QueryAST.parse(query)
            required_catalog_ids = set()
            print("AST",ast)
            for catalog_query in ast.queries:
                for condition in catalog_query.group.conditions:
                    
                    matched_items = []
                    
                    # 1. Check catalog_items based on the AST catalog_value
                    if condition.catalog_value == "TEMPORAL":
                        # We use your existing temporal resolution logic here
                        mongo_op_map = {">": "$gt", ">=": "$gte", "<": "$lt", "<=": "$lte", "=": "$eq"}
                        mongo_op = mongo_op_map.get(condition.operator, "$eq")
                        
                        target_date = condition.item_path[-1] if isinstance(condition.item_path, list) else condition.item_path
                        # Note: Assume target_date is already standardized to ISO format by the AST
                        print("BEGORE")
                        matched_items = await self.catalog_item_repository.find_by_temporal_operator(
                            mongo_op=mongo_op, 
                            target_date=target_date
                        )
                        print("MATCHED_ITEMS", matched_items)
                    else:
                        # For SPATIAL, SEX, CIE10, PLOT_TYPE
                        print("BEFORE___")
                        leaf_value = condition.item_path[-1] if isinstance(condition.item_path, list) else condition.item_path
                        print("BEFORE", leaf_value)
                        matched_items = await self.catalog_item_repository.find_by_value(leaf_value)
                        print("MATCHED_ITEMS", matched_items)

                    if not matched_items:
                        log.debug(f"Condition {condition} matched 0 items. No observatories can fulfill this.")
                        continue
                        # return Ok([])

                    # 2. Extract Catalog IDs using catalog_catalog_items_link
                    # We only need to check the first matched item, as all items 
                    # for a single condition belong to the same catalog dimension.
                    first_item_id = matched_items[0].catalog_item_id
                    print("FIRST_ITEM_ID", first_item_id)
                    # Query the junction repository you mentioned
                    # catalog_links_result = await self.catalog_catalog_item_link_repository.get_by_catalog_item_id(first_item_id)
                    catalog_links_result = await self.catalog_catalog_item_link_repository.get_catalog_id_by_catalog_item_id(first_item_id)
                    print(catalog_links_result)
                    if catalog_links_result.is_err:
                        log.error(f"Item {first_item_id} is orphaned! No catalog link found.")
                        return Err(EX.JubError(f"Database inconsistency: Item {first_item_id} has no catalog."))

                    # Add the resolved catalog ID to our required set
                    catalog_links = catalog_links_result.unwrap()
                    required_catalog_ids.add(catalog_links)

            if not required_catalog_ids:
                return Ok([])

            # ==========================================
            # STEP 3 & 4: Intersect Observatories
            # ==========================================
            catalog_ids_list = list(required_catalog_ids)
            first_catalog_id = catalog_ids_list[0]
            
            # Get observatories linked to the first required catalog
            initial_obs_links_result = await self.observatory_catalog_link_repository.get_by_catalog_id(first_catalog_id)
            if initial_obs_links_result.is_err:
                log.error(f"Failed to fetch observatories for catalog {first_catalog_id}: {initial_obs_links_result.unwrap_err()}")
                return Err(EX.JubError(f"Failed to fetch observatories for catalog {first_catalog_id}: {initial_obs_links_result.unwrap_err()}"))
            initial_obs_links = initial_obs_links_result.unwrap()
            
            valid_observatory_ids = {link.observatory_id for link in initial_obs_links}

            # Intersect with the remaining required catalogs
            for cat_id in catalog_ids_list[1:]:
                initial_obs_links_result = await self.observatory_catalog_link_repository.get_by_catalog_id(cat_id)
                if initial_obs_links_result.is_err:
                    log.error(f"Failed to fetch observatories for catalog {cat_id}: {initial_obs_links_result.unwrap_err()}")
                    return Err(EX.JubError(f"Failed to fetch observatories for catalog {cat_id}: {initial_obs_links_result.unwrap_err()}"))
                obs_links = initial_obs_links_result.unwrap()
                obs_ids_for_this_cat = {link.observatory_id for link in obs_links}
                
                valid_observatory_ids.intersection_update(obs_ids_for_this_cat)
                
                if not valid_observatory_ids:
                    break

            # Fetch the final Observatory models
            if not valid_observatory_ids:
                return Ok([])

            observatory_tasks = [
                self.observatory_repository.get_by_id(obs_id) 
                for obs_id in valid_observatory_ids
            ]
            
            raw_observatories = await asyncio.gather(*observatory_tasks)
            
            dtos = [DTO.ObservatoryXDTO.from_model(obs.unwrap()) for obs in raw_observatories if obs.is_ok]
            return Ok(dtos)
        except Exception as e:
            log.error({
                "message": "Error during observatory search",
                "error": str(e),                 
                "query": query
            })
            return Err(EX.JubError.from_exception(e))
        
    async def search(self,query:str)->Result[DTO.ProductXDTO, EX.JubError]:
        """
        Takes raw ProductX models, resolves their graph relationships to get 
        catalog item names, and returns fully hydrated ProductXDTOs.
        """
        products_result = await self.execute_query(query)
        if products_result.is_err:
            return Err(products_result.unwrap_err())
        

        products = products_result.unwrap()  
        if not products:
            return Ok([])

        # 1. Extract all product IDs
        product_ids = [p.product_id for p in products]

        # 2. Fetch all links for these products concurrently.
        # (Note: Adjust 'get_by_product_id' to match your repository's actual method name)
        link_tasks = [
            self.product_catalog_item_link_repository.get_by_product_id(pid)
            for pid in product_ids
        ]
        links_results = await asyncio.gather(*link_tasks)

        links:List[List[M.CatalogItemToProductLink]] = []
        for l in links_results:
            if l.is_err:
                log.error(f"Failed to fetch product catalog item links: {l.unwrap_err()}")
                continue
            links.append(l.unwrap())




        # 3. Map product_id -> list of catalog_item_ids and gather unique item IDs
        product_to_item_ids = {}
        unique_item_ids = set()

        for pid, catalog_items_links in zip(product_ids, links):
            # Assuming your link model has a property called 'catalog_item_id'
            # If your repo returns None for empty links, we handle it safely:
            if catalog_items_links:
                item_ids = [link.catalog_item_id for link in catalog_items_links]
            else:
                item_ids = []
                
            product_to_item_ids[pid] = item_ids
            unique_item_ids.update(item_ids)

        # 4. Fetch the actual Catalog Items to get their human-readable names
        # (Note: Adjust 'get' to match your repository's actual method name)
        item_tasks = [
            self.catalog_item_repository.get_by_id(item_id) 
            for item_id in unique_item_ids
        ]
        catalog_items = await asyncio.gather(*item_tasks)

        # 5. Create a fast lookup dictionary: item_id -> item name
        item_lookup= {}
        for item in catalog_items: 
            if item.is_err:
                log.error(f"Failed to fetch catalog item {item.unwrap_err()}")
                continue
            item_model = item.unwrap()
            item_lookup[item_model.catalog_item_id] = item_model.name
            
            
            
        # item_lookup = {
        #     item.catalog_item_id: item.name
        #     for item in catalog_items if item is not None
        # }

        # 6. Hydrate and build the DTOs
        response_dtos = []
        for p in products:
            # Get the raw item IDs linked to this specific product
            p_item_ids = product_to_item_ids.get(p.product_id, [])
            
            # Translate IDs to names
            human_readable_attributes = [
                item_lookup.get(i_id, i_id) # Fallback to the raw ID if the name is missing
                for i_id in p_item_ids
            ]

            # Build the DTO. We can use the raw IDs as 'tags' and the names as 'attributes'!
            dto = DTO.ProductXDTO.from_model(
                model=p,
                # attributes_names=human_readable_attributes,
                # tags=p_item_ids 
            )
            dto.tags = p_item_ids
            dto.attributes = human_readable_attributes
            response_dtos.append(dto)

        return Ok(response_dtos)

    async def _get_canonical_id(self, raw_target: str) -> Result[str, EX.JubError]:
            """
            Intercepts a raw string from the AST. 
            If it's an alias (e.g., '28'), it returns the real ID (e.g., 'TAM').
            If it's not an alias, it assumes it's already the real ID.
            """
            try:
                # 1. Search the alias table for this exact string
                alias_cursor = self.catalog_alias_repository.collection.find({"value": raw_target})
                alias_docs = await alias_cursor.to_list(length=1)
                
                if alias_docs:
                    alias_id = alias_docs[0]["catalog_item_alias_id"]
                    
                    # 2. Find which canonical item this alias points to
                    link_cursor = self.catalog_item_catalog_alias_link_repository.collection.find({"catalog_item_alias_id": alias_id})
                    link_docs = await link_cursor.to_list(length=1)
                    
                    if link_docs:
                        return Ok(link_docs[0]["catalog_item_id"])
                        
                # 3. If it's not in the alias table, we assume the user typed the canonical ID directly
                return Ok(raw_target)
                
            except Exception as e:
                log.error(f"Error resolving alias for {raw_target}: {e}")
                return Err(EX.JubError.from_exception(e))       
    def __is_global_wildcard(self, condition: Condition) -> bool:
            """Checks if the user just passed '*' with no prefix (e.g., VS(*))."""
            path = condition.item_path
            # Check for strings "*", "", or lists ["*"], []
            if isinstance(path, list):
                return len(path) == 0 or (len(path) == 1 and path[0] == "*")
            return path == "*" or path == ""
    async def execute_query(self, query_str: str, observatory_id: Optional[str] = None) -> Result[List[M.ProductX], EX.JubError]:
        """
        The main entry point for the Jub search bar.
        """
        try:
            # 1. Parse string to AST
            ast = QueryAST.parse(query_str)
            print("AST",ast)
            # 2. Resolve AST conditions into required sets of Catalog Item IDs
            required_sets_res = await self._build_required_sets(ast)
            print(required_sets_res)

            print("_"*20)
            if required_sets_res.is_err:
                return required_sets_res
            
            required_sets = required_sets_res.unwrap()
            
            # 3. Build and execute the aggregation pipeline
            pipeline = self._build_mongo_pipeline(observatory_id, required_sets)
            
            cursor = self.observatory_product_link_repository.collection.aggregate(pipeline)
            documents = await cursor.to_list(length=None)
            
            # 4. Return formatted products
            products = [M.ProductX(**doc) for doc in documents]
            return Ok(products)
            
        except Exception as e:
            log.error(f"Execution failed for query '{query_str}': {e}")
            return Err(EX.JubError.from_exception(e))

    async def _build_required_sets(self, ast: QueryAST) -> Result[List[List[str]], EX.JubError]:
        """
        Converts the AST into a list of required tag lists.
        A product MUST have at least one matching tag from EVERY list in required_sets.
        """
        try: 
            required_sets: List[List[str]] = []
            for query in ast.queries:
                # If OR/SINGLE logic: All conditions pool together into ONE requirement set.
                if query.group.logic in ["OR", "SINGLE"]:
                    # We combine all conditions into one big set. The product needs at least one tag from this combined set to satisfy the OR logic.
                    combined_set = set([])
                    # skip_group is a flag to identify if we have a global wildcard in the group. If we do, we can skip processing the rest of the conditions because the wildcard already allows any tag to match.
                    skip_group = False
                    for cond in query.group.conditions:
                        if self.__is_global_wildcard(cond):
                            skip_group = True
                            break
                        # If it's not a global wildcard, we resolve the condition as normal and add its valid tags to the combined set.
                        res = await self._resolve_condition(cond)
                        if res.is_err: 
                            log.error(f"Failed to resolve condition {cond}: {res.unwrap_err()}")
                            return res
                        # combined_set.extend(res.unwrap())
                        combined_set.update(res.unwrap()) # Using a set to avoid duplicates

                    if not skip_group:
                        required_sets.append(list(combined_set))
                    
                # If AND logic: Every condition becomes its OWN separate requirement set.
                elif query.group.logic == "AND":
                    intersected_sets = None

                    for cond in query.group.conditions:
                        
                        if self.__is_global_wildcard(cond):
                            continue  # Skip this condition, it doesn't restrict the search

                        res = await self._resolve_condition(cond)
                        if res.is_err: 
                            log.error(f"Failed to resolve condition {cond}: {res.unwrap_err()}")
                            return res
                        conds_ids = set(res.unwrap())

                        if intersected_sets is None:
                            intersected_sets = conds_ids
                        else:                            
                            intersected_sets = intersected_sets.intersection(conds_ids)

                    if intersected_sets is not None:
                        required_sets.append(list(intersected_sets))

            # print("REQUIRED",required_sets)
            return Ok(required_sets)
        except Exception as e:
            log.error({
                "message": "Error building required sets from AST",
                "error": str(e),
            })
            return Err(EX.JubError.from_exception(e))

    async def _resolve_condition(self, condition: Condition) -> Result[List[str], EX.JubError]:
        """
        Translates a single AST condition into an exact list of catalog_item_ids.
        """
        try:
            log.debug({
                "event":"CONDITION_RESOLUTION",
                "message": "Resolving condition",
                "condition": condition.model_dump()
            })
            if condition.catalog_value == "TEMPORAL" and condition.operator not in ["WILDCARD"]:
                mongo_op_map = {
                    ">": "$gt", ">=": "$gte", "<": "$lt", "<=": "$lte", "=": "$eq",
                    "EXACT": "$eq" 
                }
                mongo_op     = mongo_op_map.get(condition.operator)
                if not mongo_op:
                    return Err(EX.UnknownError(f"Unsupported operator for temporal condition: {condition.operator}"))

                path_val = condition.item_path[-1] if isinstance(condition.item_path, list) and len(condition.item_path) > 0 else condition.item_path
                
                try:
                    dt_val = DT.datetime.fromisoformat(path_val.replace("Z", "+00:00"))  # Convert ISO string to datetime object
                except ValueError as ve:
                    log.error(f"Invalid datetime format for temporal condition: {path_val}")
                    return Err(EX.JubError(f"Invalid datetime format for temporal condition: {path_val}"))


                # Query the catalog items to find which IDs fall in this date range
                cursor = self.catalog_item_repository.collection.find(
                    # Assuming temporal values are stored as ISO strings in 'value'
                    {"value_type": "DATETIME", "temporal_value": {mongo_op: dt_val}}
                )
                docs = await cursor.to_list(length=None)
                log.debug({
                    "event": "TEMPORAL_CONDITION_RESOLUTION",
                    "message": "Resolved temporal condition",
                    "path_val": path_val,
                    "mongo_op": mongo_op,
                    "dt_val": dt_val.isoformat(),
                    "condition": condition.model_dump(),
                    "resolved_ids": [doc["catalog_item_id"] for doc in docs]
                })
                return Ok([doc["catalog_item_id"] for doc in docs])


            path       = condition.item_path
            is_list    = isinstance(path, list)
            raw_target = ""
            # Extract target ID from the path (e.g., "CIE10.C50" -> "C50")
            # target_id = condition.item_path[-1] if isinstance(condition.item_path, list) else condition.item_path


            # Handle EXACT
            log.debug({
                "event": "CONDITION_RESOLUTION",
                "message": "Handling exact condition",
                "operator": condition.operator,
                "item_path": condition.item_path
            })
            if condition.operator == "WILDCARD":
                path_len = len(path)
                if is_list:
                    # Scenario A: The parser left the '*' in the list (e.g., ['MX', 'TAMPS', '*'])
                    if path_len > 1 and path[-1] == "*":
                        raw_target = path[-2]
                    # Scenario B: The parser stripped the '*' (e.g., ['MX', 'TAMPS'])
                    elif path_len > 0 and path[-1] != "*":
                        raw_target = path[-1]
                    # Scenario C: Reverse wildcard (e.g., ['*', 'MX'])
                    elif path_len > 0 and path[0] == "*":
                        raw_target = path[-1]
                    else:
                        return Err(EX.JubError(f"Invalid wildcard list format: {path}"))
                else:
                    # Handle raw strings
                    if path.endswith(".*"):
                        raw_target = path[:-2]
                    elif path != "*":
                        raw_target = path  # The parser just sent "TAMPS" with a WILDCARD operator
                    else:
                        raw_target = path # Global wildcard handling

                # return Err(EX.JubError(f"Invalid wildcard format in condition: {condition}"))
            elif condition.operator == "EXACT":
                raw_target = path[-1] if is_list else path
            else:
                return Err(EX.UnknownError(f"Unsupported operator in condition: {condition.operator}"))



            # Alias resolution: If the user typed an alias (e.g., '28'), we need to find the canonical ID (e.g., 'TAM') 
            canonical_res = await self._get_canonical_id(raw_target)
            
            if canonical_res.is_err:
                log.error(f"Failed to resolve canonical ID for {raw_target}: {canonical_res.unwrap_err()}")
                return Err(EX.JubError(f"Failed to resolve canonical ID for {raw_target}: {canonical_res.unwrap_err()}"))
            target_id = canonical_res.unwrap()

            if condition.operator == ConditionOperators.WILDCARD.value:
                children_res = await self.catalog_item_relationship_repository.get_all_children_nodes(target_id)
                if children_res.is_err:
                    log.error(f"Failed to fetch children for wildcard condition {condition}: {children_res.unwrap_err()}")
                    return Err(EX.JubError(f"Failed to fetch children for wildcard condition {condition}: {children_res.unwrap_err()}"))
                valid_ids = [target_id] + children_res.unwrap()  # Include the parent ID itself
                return Ok(valid_ids)
            
            elif condition.operator == ConditionOperators.EXACT.value:
                return Ok([target_id])
            
            else:
                log.error(f"Unsupported operator in condition: {condition.operator}")
                return Err(EX.UnknownError(f"Unsupported operator in condition: {condition.operator}"))
           

        except Exception as e:
            log.error(f"Error resolving condition {condition}: {e}")
            return Err(EX.JubError.from_exception(e))

    def _build_mongo_pipeline(self, observatory_id: Optional[str], required_sets: List[List[str]]) -> List[dict]:
        """
        Translates the required_sets into a high-performance MongoDB intersection pipeline.
        If observatory_id is None, it searches across all observatories.
        """
        pipeline = []

        # 1. Scope the search strictly to this observatory (IF provided)
        if observatory_id:
            pipeline.append({"$match": {"observatory_id": observatory_id}})
            
        # 1.5. DEDUPLICATION: If searching all observatories, a product might appear multiple times 
        # if it belongs to multiple observatories. We group by product_id to ensure unique results.
        pipeline.append({
            "$group": {
                "_id": "$product_id",
                "product_id": {"$first": "$product_id"}
            }
        })

        # 2. Join the product's tags from the linking table
        pipeline.append({
            "$lookup": {
                "from": self.product_catalog_item_link_repository.collection.name,
                "localField": "product_id",
                "foreignField": "product_id",
                "as": "raw_tags"
            }
        })

        # 3. Transform the array of link objects into a simple array of strings (IDs)
        pipeline.append({
            "$project": {
                "product_id": 1,
                "matched_tags": {
                    "$map": {
                        "input": "$raw_tags",
                        "as": "tag_doc",
                        "in": "$$tag_doc.catalog_item_id"
                    }
                }
            }
        })

        # 4. Apply the logical intersections parsed from the AST (ONLY if there are requirements)
        if required_sets:
            intersection_conditions = [
                {"$gt": [{"$size": {"$setIntersection": ["$matched_tags", req_set]}}, 0]}
                for req_set in required_sets
            ]
            
            pipeline.append({
                "$match": {
                    "$expr": {
                        "$and": intersection_conditions
                    }
                }
            })

        # 5. Fetch the actual product metadata for the surviving IDs
        pipeline.extend([
            {"$lookup": {
                "from": self.product_repository.collection.name,
                "localField": "product_id",
                "foreignField": "product_id",
                "as": "product_data"
            }},
            {"$unwind": "$product_data"},
            {"$replaceRoot": {"newRoot": "$product_data"}}
        ])

        return pipeline


