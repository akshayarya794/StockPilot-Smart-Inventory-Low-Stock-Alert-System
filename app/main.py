import csv
import io
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import PORT, HOST
from app.database import init_db, check_db_health
from app.models import (
    get_all_products,
    get_product_by_id,
    create_product,
    update_product,
    adjust_stock,
    delete_product,
    get_inventory_summary,
    ProductNotFoundError,
    DuplicateSKUError,
    NegativeStockError,
)
from app.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    InventorySummary,
    StockAdjustRequest,
    HealthResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes the database schema and seeds demo products upon startup."""
    init_db()
    yield


app = FastAPI(
    title="StockPilot — Smart Inventory & Low-Stock Alert System",
    description="Containerized FastAPI web application and REST API for real-time inventory tracking and low-stock alerting.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for cross-origin frontend interactions if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and Static configuration
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ---------------------------------------------------------
# Web Dashboard Frontend (Section 6)
# ---------------------------------------------------------
@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["Dashboard"],
    summary="Interactive StockPilot Inventory Dashboard",
)
def get_dashboard(request: Request):
    """Renders the server-side dashboard UI with real-time API hydration."""
    summary_data = get_inventory_summary()
    items_data = get_all_products()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "summary": summary_data,
            "products": items_data,
        },
    )


# ---------------------------------------------------------
# Health Check Endpoint (Docker HEALTHCHECK / CloudWatch / ALB)
# ---------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="System and Database Health Check",
)
def get_health():
    """
    Executes a lightweight SELECT 1 query against SQLite.
    Returns 200 OK when healthy, or 503 Service Unavailable if SQLite is unreachable.
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    is_connected = check_db_health()

    if not is_connected:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "service": "stockpilot-fastapi",
                "database": "disconnected",
                "timestamp": now_iso,
            },
        )

    return {
        "status": "ok",
        "service": "stockpilot-fastapi",
        "database": "connected",
        "timestamp": now_iso,
    }


# ---------------------------------------------------------
# Inventory REST API Endpoints
# ---------------------------------------------------------
@app.get(
    "/api/products",
    response_model=ProductListResponse,
    tags=["Products"],
    summary="List all products with summary KPIs and optional filtering",
)
def list_products(
    search: Optional[str] = Query(None, description="Search across name, SKU, or category"),
    low_stock_only: bool = Query(False, description="Filter to show only products with quantity <= reorder_level"),
):
    """
    Returns total catalog metrics and product listings.
    Items automatically include computed `is_low_stock` flag.
    """
    summary_data = get_inventory_summary()
    items_data = get_all_products(search=search, low_stock_only=low_stock_only)

    return {
        "summary": summary_data,
        "items": items_data,
    }


@app.get(
    "/api/products/{product_id}",
    response_model=ProductResponse,
    tags=["Products"],
    summary="Get single product details by ID",
)
def get_product(product_id: int):
    """Retrieves product by ID or returns 404 if not found."""
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    return product


@app.post(
    "/api/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Products"],
    summary="Create a new product",
)
def create_new_product(product_in: ProductCreate):
    """
    Creates a new product in the catalog.
    Rejects duplicate SKU with 409 Conflict.
    Rejects negative values with 422 Unprocessable Entity.
    """
    try:
        created = create_product(product_in)
        return created
    except DuplicateSKUError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


def _handle_stock_adjustment(product_id: int, adjust_data: StockAdjustRequest):
    """Helper method to execute stock adjustment for PATCH and POST routes."""
    try:
        updated = adjust_stock(
            product_id=product_id,
            delta=adjust_data.delta,
            new_quantity=adjust_data.new_quantity,
        )
        return updated
    except ProductNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    except NegativeStockError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock quantity cannot be negative",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.patch(
    "/api/products/{product_id}/stock",
    response_model=ProductResponse,
    tags=["Products"],
    summary="Adjust product stock quantity (delta or new_quantity)",
)
def patch_stock(product_id: int, adjust_data: StockAdjustRequest):
    """
    Adjusts stock by positive/negative delta or absolute new_quantity.
    Strictly returns HTTP 400 if resulting quantity < 0.
    """
    return _handle_stock_adjustment(product_id, adjust_data)


@app.post(
    "/api/products/{product_id}/stock",
    response_model=ProductResponse,
    tags=["Products"],
    summary="Adjust product stock quantity (POST alternative)",
)
def post_stock(product_id: int, adjust_data: StockAdjustRequest):
    """Alternative POST endpoint for stock adjustment."""
    return _handle_stock_adjustment(product_id, adjust_data)


@app.put(
    "/api/products/{product_id}",
    response_model=ProductResponse,
    tags=["Products"],
    summary="Update product details",
)
def update_product_details(product_id: int, product_update: ProductUpdate):
    """Updates product attributes and updates timestamp."""
    try:
        updated = update_product(product_id, product_update)
        return updated
    except ProductNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    except DuplicateSKUError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.delete(
    "/api/products/{product_id}",
    tags=["Products"],
    summary="Delete a product from the catalog",
)
def delete_product_endpoint(product_id: int):
    """Deletes a product by ID."""
    deleted = delete_product(product_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    return {"message": f"Product {product_id} deleted successfully", "id": product_id}


@app.get(
    "/api/export/csv",
    tags=["Export"],
    summary="Export current inventory catalog to CSV",
)
def export_inventory_csv():
    """Generates and downloads a timestamped CSV snapshot of the catalog."""
    products = get_all_products()
    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV Header
    writer.writerow(["ID", "Name", "Category", "SKU", "Quantity", "Reorder Level", "Status", "Updated At"])

    # Write Product Rows
    for p in products:
        status_text = "LOW STOCK" if p["is_low_stock"] else "IN STOCK"
        writer.writerow([
            p["id"],
            p["name"],
            p["category"],
            p["sku"],
            p["quantity"],
            p["reorder_level"],
            status_text,
            p["updated_at"],
        ])

    csv_content = output.getvalue()
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stockpilot_inventory_{timestamp_str}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
