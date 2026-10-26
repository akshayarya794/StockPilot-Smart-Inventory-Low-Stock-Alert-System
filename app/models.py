import sqlite3
from typing import Optional, List, Dict, Any
from app.database import get_db_connection
from app.schemas import ProductCreate, ProductUpdate


class ProductNotFoundError(Exception):
    """Raised when a product with given ID is not found."""
    pass


class DuplicateSKUError(Exception):
    """Raised when attempting to create or update a product with an existing SKU."""
    pass


class NegativeStockError(Exception):
    """Raised when a stock adjustment would result in a negative quantity."""
    pass


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a sqlite3.Row to a standard dictionary with computed is_low_stock."""
    data = dict(row)
    data["is_low_stock"] = data["quantity"] <= data["reorder_level"]
    return data


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single product by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?;", (product_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single product by SKU."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE sku = ? COLLATE NOCASE;", (sku.strip().upper(),))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_all_products(search: Optional[str] = None, low_stock_only: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves products with optional search and low-stock filters.
    Sorted so low-stock items appear first, followed by product ID.
    """
    query = "SELECT * FROM products WHERE 1=1"
    params: List[Any] = []

    if search:
        search_term = f"%{search.strip()}%"
        query += " AND (name LIKE ? OR sku LIKE ? OR category LIKE ?)"
        params.extend([search_term, search_term, search_term])

    if low_stock_only:
        query += " AND quantity <= reorder_level"

    query += " ORDER BY (quantity <= reorder_level) DESC, id ASC;"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [row_to_dict(row) for row in rows]


def get_inventory_summary() -> Dict[str, int]:
    """Computes total products, total units, and low-stock count."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                COUNT(*) AS total_products,
                COALESCE(SUM(quantity), 0) AS total_units,
                COALESCE(SUM(CASE WHEN quantity <= reorder_level THEN 1 ELSE 0 END), 0) AS low_stock_count
            FROM products;
            """
        )
        row = cursor.fetchone()
        return {
            "total_products": row["total_products"],
            "total_units": row["total_units"],
            "low_stock_count": row["low_stock_count"],
        }


def create_product(product: ProductCreate) -> Dict[str, Any]:
    """Creates a new product in the database. Enforces unique SKU and non-negative constraints."""
    sku = product.sku.strip().upper()
    existing = get_product_by_sku(sku)
    if existing:
        raise DuplicateSKUError(f"A product with SKU '{sku}' already exists.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO products (name, category, sku, quantity, reorder_level)
                VALUES (?, ?, ?, ?, ?);
                """,
                (product.name.strip(), product.category.strip(), sku, product.quantity, product.reorder_level),
            )
            conn.commit()
            new_id = cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e).upper():
                raise DuplicateSKUError(f"A product with SKU '{sku}' already exists.")
            raise ValueError(f"Database constraint violation: {e}")

    created = get_product_by_id(new_id)
    if not created:
        raise RuntimeError("Failed to retrieve created product.")
    return created


def update_product(product_id: int, product_update: ProductUpdate) -> Dict[str, Any]:
    """Updates an existing product's fields."""
    existing = get_product_by_id(product_id)
    if not existing:
        raise ProductNotFoundError(f"Product with ID {product_id} not found.")

    update_dict = product_update.model_dump(exclude_unset=True)
    if not update_dict:
        return existing

    if "sku" in update_dict and update_dict["sku"]:
        new_sku = update_dict["sku"].strip().upper()
        sku_match = get_product_by_sku(new_sku)
        if sku_match and sku_match["id"] != product_id:
            raise DuplicateSKUError(f"A product with SKU '{new_sku}' already exists.")
        update_dict["sku"] = new_sku

    set_clauses = [f"{col} = ?" for col in update_dict.keys()]
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    values = list(update_dict.values())
    values.append(product_id)

    query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?;"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e).upper():
                raise DuplicateSKUError(f"SKU already in use by another product.")
            raise ValueError(f"Constraint violation: {e}")

    updated = get_product_by_id(product_id)
    if not updated:
        raise ProductNotFoundError(f"Product with ID {product_id} not found.")
    return updated


def adjust_stock(product_id: int, delta: Optional[int] = None, new_quantity: Optional[int] = None) -> Dict[str, Any]:
    """
    Adjusts stock using either delta or direct new_quantity.
    Strictly prevents negative stock count.
    """
    existing = get_product_by_id(product_id)
    if not existing:
        raise ProductNotFoundError(f"Product with ID {product_id} not found.")

    current_qty = existing["quantity"]

    if new_quantity is not None:
        if new_quantity < 0:
            raise NegativeStockError("Stock quantity cannot be negative")
        final_qty = new_quantity
    elif delta is not None:
        final_qty = current_qty + delta
        if final_qty < 0:
            raise NegativeStockError(
                f"Stock quantity cannot be negative. Current stock is {current_qty}, adjustment requested: {delta}."
            )
    else:
        raise ValueError("Either delta or new_quantity must be provided.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE products 
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?;
            """,
            (final_qty, product_id),
        )
        conn.commit()

    updated = get_product_by_id(product_id)
    if not updated:
        raise ProductNotFoundError(f"Product with ID {product_id} not found.")
    return updated


def delete_product(product_id: int) -> bool:
    """Deletes a product by ID. Returns True if deleted, False if not found."""
    existing = get_product_by_id(product_id)
    if not existing:
        return False

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?;", (product_id,))
        conn.commit()
        return cursor.rowcount > 0
