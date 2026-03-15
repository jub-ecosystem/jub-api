from jubapi.repositories.v2.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorCollection as Collection
import datetime as DT
import jubapi.models.v2 as M
from typing import List
from option import Result,Err,Ok
import jubapi.errors as EX
from jubapi.log.log import Log
import os

log = Log(
    name = __name__,
    path = os.environ.get("JUB_LOG_PATH", "/log")
)


class ObservatoriesRepository(BaseRepository[M.ObservatoryX]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.ObservatoryX, "observatory_id")

class ProductsRepository(BaseRepository[M.ProductX]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.ProductX, "product_id")

class CatalogsRepository(BaseRepository[M.CatalogX]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.CatalogX, "catalog_id")
    async def get_catalog_by_catalog_type(self, catalog_type:str)->Result[List[M.CatalogX],EX.JubError]:
        try: 
            result = self.collection.find({"catalog_type": catalog_type})
            items = await result.to_list(length=None)
            models:List[M.CatalogX] = []
            for item in items:
                m = M.CatalogX(
                    catalog_id        = item.get('catalog_id',""),
                    catalog_type      = item.get('catalog_type',""),
                    description       = item.get('description',""),
                    level             = item.get('level',0),
                    name              = item.get('name',""),
                    value             = item.get('value',""),
                    parent_catalog_id = item.get('parent_catalog_id',None),
                    root_group_id     = item.get('root_group_id',None),
                    created_at        = item.get('created_at',DT.datetime.now(DT.timezone.utc) ),
                    updated_at        = item.get('updated_at',DT.datetime.now(DT.timezone.utc) )
                )
                models.append(m)
                
                # log.info(f"Found Catalog: {item}")
            return Ok(models)
        except Exception as e:
            return Err(EX.JubError.from_exception(e))


class CatalogItemsRepository(BaseRepository[M.CatalogItemX]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.CatalogItemX, "catalog_item_id")

    async def find_by_value(self, search_value: str) -> List[M.CatalogItemX]:
            """
            Finds catalog items that exactly match the given string value.
            """
            try:
                # Query the collection for an exact match on the 'value' field
                cursor = self.collection.find({"value": search_value})
                
                # Fetch all matching documents and map them to models
                docs = await cursor.to_list(length=None)
                return [M.CatalogItemX.from_doc(doc) for doc in docs]
                
            except Exception as e:
                log.error(f"Error querying catalog items by value '{search_value}': {e}")
                return []

    async def find_by_temporal_operator(self, mongo_op: str, target_date: str) -> List[M.CatalogItemX]:
            """
            Finds catalog items based on a temporal operator and date.
            """
            try:
                # 1. Convert the standardized ISO string to a Python datetime object
                # MongoDB requires native datetime objects to run operators like $gte and $lte correctly.
                if isinstance(target_date, str):
                    dt_val = DT.datetime.fromisoformat(target_date.replace("Z", "+00:00"))
                else:
                    dt_val = target_date

                # 2. Query the collection
                cursor = self.collection.find({
                    "value_type": "DATETIME", # Ensure this matches your Enum if you use one (e.g., M.CatalogItemValueType.DATETIME)
                    "temporal_value": {mongo_op: dt_val}
                })
                
                # 3. Fetch and map to models
                docs = await cursor.to_list(length=None)
                return [M.CatalogItemX.from_doc(doc) for doc in docs]
                
            except Exception as e:
                # Depending on how your repo handles errors, you might want to log this or raise a custom error.
                log.error(f"Error querying temporal operator {mongo_op} with date {target_date}: {e}")
                return []

class CatalogItemAliasesRepository(BaseRepository[M.CatalogItemAlias]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.CatalogItemAlias, "catalog_item_alias_id")


# 1. Observatory <-> Product
class ObservatoryToProductLinkRepository(BaseRepository[M.ObservatoryToProductLink]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.ObservatoryToProductLink, "observatory_id")

# 2. Observatory <-> Catalog
class ObservatoryToCatalogLinkRepository(BaseRepository[M.ObservatoryToCatalogLink]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.ObservatoryToCatalogLink, "observatory_id")
    async def get_by_catalog_id(self, catalog_id:str)->Result[List[M.ObservatoryToCatalogLink],EX.JubError]:
        try: 
            result = self.collection.find({"catalog_id": catalog_id})
            items = await result.to_list(length=None)
            models:List[M.ObservatoryToCatalogLink] = []
            for item in items:
                m = M.ObservatoryToCatalogLink(
                    observatory_id = item.get('observatory_id',""),
                    catalog_id     = item.get('catalog_id',"")
                )
                models.append(m)
                
                # log.info(f"Found ObservatoryToCatalogLink: {item}")
            return Ok(models)
        except Exception as e:
            return Err(EX.JubError.from_exception(e))

# 3. Catalog -> Catalog Item
class CatalogToCatalogItemLinkRepository(BaseRepository[M.CatalogToCatalogItemLink]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.CatalogToCatalogItemLink, "catalog_id")
    async def get_by_catalog_item_id(self, catalog_item_id:str)->Result[List[M.CatalogToCatalogItemLink],EX.JubError]:
        try: 
            result = self.collection.find({"catalog_item_id": catalog_item_id})
            items = await result.to_list(length=None)
            models:List[M.CatalogToCatalogItemLink] = []
            for item in items:
                m = M.CatalogToCatalogItemLink(
                    catalog_id      = item.get('catalog_id',""),
                    catalog_item_id = item.get('catalog_item_id',"")
                )
                models.append(m)
                
                # log.info(f"Found CatalogToCatalogItemLink: {item}")
            return Ok(models)
        except Exception as e:
            return Err(EX.JubError.from_exception(e))
    async def get_catalog_id_by_catalog_item_id(self, catalog_item_id:str)->Result[str,EX.JubError]:
        try: 
            result = await self.collection.find_one({"catalog_item_id": catalog_item_id})
            if not result:
                return Err(EX.NotFound(f"No catalog link found for item {catalog_item_id}"))
            catalog_id = result.get('catalog_id',"")
            return Ok(catalog_id)
        except Exception as e:
            return Err(EX.JubError.from_exception(e))

# 4. Product -> Catalog Item 
class ProductToCatalogItemLinkRepository(BaseRepository[M.CatalogItemToProductLink]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.CatalogItemToProductLink, "product_id")
    
    async def get_by_product_id(self,product_id:str)->Result[List[M.CatalogItemToProductLink],EX.JubError]:
        try: 
            result = self.collection.find({"product_id": product_id})
            items = await result.to_list(length=None)
            models:List[M.CatalogItemToProductLink] = []
            for item in items:
                m = M.CatalogItemToProductLink(
                    product_id      = item.get('product_id',""),
                    catalog_item_id = item.get('catalog_item_id',"")
                )
                models.append(m)
                
                # log.info(f"Found CatalogItemToProductLink: {item}")
            return Ok(models)
        except Exception as e:
            return Err(EX.JubError.from_exception(e))





# Catalog Item Value -> Catalog Item (The Alias Engine)
class CatalogItemToCatalogAliasLinkRepository(BaseRepository[M.CatalogItemToCatalogAliasLink]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.CatalogItemToCatalogAliasLink, "catalog_item_id")

# 5. Catalog Item -> Catalog Item (The Hierarchy Engine)
class CatalogItemRelationshipRepository(BaseRepository[M.CatalogItemRelationship]):
    def __init__(self, collection: Collection):
        super().__init__(collection, M.CatalogItemRelationship, "parent_id")

    
    async def get_all_children_nodes(self, root_parent_id: str,length:int = None) -> Result[List[str], EX.JubError]:
        """
        This hides the MongoDB $graphLookup logic.
        It resolves wildcards like MX.* by fetching the ID of every child node.
        """
        try: 
            pipeline = [
                {"$match": {"parent_id": root_parent_id}},
                {"$graphLookup": {
                    "from": self.collection.name,
                    "startWith": "$child_id",
                    "connectFromField": "child_id",
                    "connectToField": "parent_id",
                    "as": "descendants"
                }}
            ]
            
            cursor = self.collection.aggregate(pipeline) 
            results = await cursor.to_list(length=length)
            
            # Parse the results to return a simple list of child IDs
            descendant_ids = set()
            for doc in results:
                descendant_ids.add(doc["child_id"])
                for desc in doc.get("descendants", []):
                    descendant_ids.add(desc["child_id"])
                    
            return Ok(list(descendant_ids))
        except Exception as e:
            log.error(f"Error in get_all_children_nodes: {e}")
            return Err(EX.JubError.from_exception(e))



