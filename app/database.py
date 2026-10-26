import sqlite3
from typing import Generator
from app.config import DB_PATH

DEMO_PRODUCTS = [
    {
        "name": "Wireless Barcode Scanner",
        "category": "Electronics",
        "sku": "SP-EL-101",
        "quantity": 25,
        "reorder_level": 10,
    },
    {
        "name": "Thermal Receipt Paper (Pack of 10)",
        "category": "Supplies",
        "sku": "SP-SU-204",
        "quantity": 4,
        "reorder_level": 15,
    },
    {
        "name": "USB-C POS Dock",
        "category": "Electronics",
        "sku": "SP-EL-109",
        "quantity": 8,
        "reorder_level": 8,
    },
    {
        "name": "Organic Arabica Coffee Beans 1kg",
        "category": "Beverages",
        "sku": "SP-BV-301",
        "quantity": 42,
        "reorder_level": 12,
    },
    {
        "name": "Heavy Duty Packing Tape",
        "category": "Packaging",
        "sku": "SP-PK-405",
        "quantity": 2,
        "reorder_level": 10,
    },
    {
        "name": "Cardboard Shipping Boxes (Medium)",
        "category": "Packaging",
        "sku": "SP-PK-410",
        "quantity": 60,
        "reorder_level": 20,
    },
]


def get_db_connection() -> sqlite3.Connection:
    """Creates a new SQLite connection with sqlite3.Row row_factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys and CHECK constraint enforcement
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initializes tables and seeds demo products if the database is empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                sku TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL CHECK(quantity >= 0),
                reorder_level INTEGER NOT NULL DEFAULT 10 CHECK(reorder_level >= 0),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    seed_demo_data()


def seed_demo_data() -> None:
    """Seeds the 6 demo retail products if the products table is empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM products;")
        count = cursor.fetchone()["count"]
        if count == 0:
            cursor.executemany(
                """
                INSERT INTO products (name, category, sku, quantity, reorder_level)
                VALUES (:name, :category, :sku, :quantity, :reorder_level);
                """,
                DEMO_PRODUCTS,
            )
            conn.commit()


def check_db_health() -> bool:
    """Executes a lightweight SELECT 1 query to verify database health."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            return result is not None and result[0] == 1
    except Exception:
        return False
