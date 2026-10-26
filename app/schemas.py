from typing import Optional, List
from datetime import datetime
# pyrefly: ignore[missing-import]
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Product display name")
    category: str = Field(..., min_length=2, max_length=100, description="Retail category")
    sku: str = Field(..., min_length=2, max_length=50, description="Unique Stock Keeping Unit")
    quantity: int = Field(..., ge=0, description="Current stock count (must be non-negative)")
    reorder_level: int = Field(default=10, ge=0, description="Low-stock threshold")

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        trimmed = v.strip().upper()
        if len(trimmed) < 2:
            raise ValueError("SKU must contain at least 2 non-whitespace characters")
        return trimmed

    @field_validator("name", "category")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 2:
            raise ValueError("Field must contain at least 2 non-whitespace characters")
        return trimmed


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    sku: Optional[str] = Field(None, min_length=2, max_length=50)
    quantity: Optional[int] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip().upper()
            if len(trimmed) < 2:
                raise ValueError("SKU must contain at least 2 non-whitespace characters")
            return trimmed
        return v

    @field_validator("name", "category")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if len(trimmed) < 2:
                raise ValueError("Field must contain at least 2 non-whitespace characters")
            return trimmed
        return v


class StockAdjustRequest(BaseModel):
    delta: Optional[int] = Field(None, description="Adjustment to stock (can be positive or negative)")
    new_quantity: Optional[int] = Field(None, ge=0, description="Direct new stock count (must be non-negative)")

    @model_validator(mode="after")
    def validate_adjustment(self) -> "StockAdjustRequest":
        if self.delta is None and self.new_quantity is None:
            raise ValueError("Either 'delta' or 'new_quantity' must be provided.")
        if self.delta is not None and self.new_quantity is not None:
            raise ValueError("Provide either 'delta' or 'new_quantity', not both.")
        return self


class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    sku: str
    quantity: int
    reorder_level: int
    updated_at: str
    is_low_stock: bool

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_row(cls, row) -> "ProductResponse":
        quantity = row["quantity"]
        reorder_level = row["reorder_level"]
        return cls(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            sku=row["sku"],
            quantity=quantity,
            reorder_level=reorder_level,
            updated_at=str(row["updated_at"]),
            is_low_stock=(quantity <= reorder_level),
        )


class InventorySummary(BaseModel):
    total_products: int
    total_units: int
    low_stock_count: int


class ProductListResponse(BaseModel):
    summary: InventorySummary
    items: List[ProductResponse]


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    timestamp: str
