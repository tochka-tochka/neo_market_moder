from pydantic import BaseModel
from typing import Dict, List
from datetime import date
from enum import Enum

class Seller(BaseModel):
    username: str

class ProductStatus(str, Enum):
    ON_MODERATION = 'on_moderation'
    ACCEPTED = 'accepted'
    BLOCKED = 'blocked'

class Category(BaseModel):
    id: str
    value: str

class Image(BaseModel):
    id: str
    url: str
    order: int
    created_at: date

class SKU(BaseModel):
    id: str
    name: str
    price: int
    characteristics: Dict[str,str]
    active_quantity: int

class Product(BaseModel):
    id: str
    title: str
    description: str
    category: Category
    characteristics: Dict[str,str]
    status: ProductStatus
    seller: Seller
    images: List[Image]
    skus: List[SKU]

