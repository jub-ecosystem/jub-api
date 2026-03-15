from pydantic import BaseModel,Field
from typing import Optional,List
from jubapi.models.v2 import ObservatoryX,CatalogX


class SearchQueryDTO(BaseModel):
    query: str
    observatory_id: Optional[str] = None
    limit: Optional[int] = 10
    skip: Optional[int] = 0

class ProductXDTO(BaseModel):
    product_id: str
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    attributes:List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


    @staticmethod
    def from_model(model) -> 'ProductXDTO':
        return ProductXDTO(
            product_id = model.product_id,
            name       = model.name,
            description= model.description,
            created_at = model.created_at.isoformat(),
            updated_at = model.updated_at.isoformat()
        )

class ObservatoryXDTO(BaseModel):
    observatory_id: str
    title: str
    description: str = ""
    image_url: Optional[str] = None
    metadata: dict = {}
    created_at: str
    updated_at: str
    @staticmethod
    def from_model(model: ObservatoryX) -> 'ObservatoryXDTO':
        return ObservatoryXDTO(
            observatory_id = model.observatory_id,
            title          = model.title,
            description    = model.description,
            metadata       = model.metadata,
            created_at     = model.created_at.isoformat(),
            updated_at     = model.updated_at.isoformat()
        )

class CatalogXDTO(BaseModel):
    catalog_id: str
    root_group_id:Optional[str] = Field(default=None)
    name: str
    value: str
    catalog_type: str
    parent_catalog_id: Optional[str] = None
    level: int = 0
    description: str = ""
    metadata: dict = {}
    created_at: str
    updated_at: str
    @staticmethod
    def from_model(model:CatalogX) -> 'CatalogXDTO':
        return CatalogXDTO(
            catalog_id        = model.catalog_id,
            name              = model.name,
            value             = model.value,
            description       = model.description,
            metadata          = model.metadata,
            catalog_type      = model.catalog_type,
            parent_catalog_id = model.parent_catalog_id,
            level             = model.level,
            root_group_id     = model.root_group_id,
            created_at        = model.created_at.isoformat(),
            updated_at        = model.updated_at.isoformat()
        )