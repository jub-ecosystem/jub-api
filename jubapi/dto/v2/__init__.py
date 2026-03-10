from pydantic import BaseModel,Field
from typing import Optional,List
from jubapi.models.v2 import ObservatoryX


class SearchQueryDTO(BaseModel):
    query: str

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