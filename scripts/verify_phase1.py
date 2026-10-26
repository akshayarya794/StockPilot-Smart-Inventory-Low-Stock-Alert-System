import sys
import os

# Ensure the root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db
from app.models import get_inventory_summary, get_all_products, adjust_stock, NegativeStockError


def main():
    print("=== StockPilot Phase 1 Verification ===")
    
    # 1. Initialize database & seed demo items
    print("Initializing SQLite database & seeding data...")
    init_db()
    
    # 2. Retrieve summary statistics
    summary = get_inventory_summary()
    print(f"\nInventory Summary:")
    print(f" - Total Products: {summary['total_products']}")
    print(f" - Total Units:    {summary['total_units']}")
    print(f" - Low-Stock Items:{summary['low_stock_count']}")
    
    # 3. Retrieve and print items
    products = get_all_products()
    print(f"\nSeeded Catalog ({len(products)} products):")
    for p in products:
        status = "[LOW STOCK]" if p["is_low_stock"] else "[HEALTHY]"
        print(f"  {p['sku']:<12} | {p['name']:<35} | Qty: {p['quantity']:>2} / Reorder: {p['reorder_level']:>2} | {status}")
    
    # 4. Verify exact assertions
    assert summary["total_products"] == 6, f"Expected 6 products, got {summary['total_products']}"
    assert summary["low_stock_count"] == 3, f"Expected 3 low stock items, got {summary['low_stock_count']}"
    assert summary["total_units"] == 141, f"Expected 141 total units, got {summary['total_units']}"
    
    # 5. Test negative stock constraint logic
    test_item = products[0]
    try:
        adjust_stock(test_item["id"], delta=-9999)
        print("ERROR: Negative stock was not prevented!")
        sys.exit(1)
    except NegativeStockError:
        print("\nNegative stock prevention verification: PASSED (Prevented negative quantity)")

    print("\n>>> PHASE 1 VERIFICATION PASSED SUCCESSFULLY <<<")


if __name__ == "__main__":
    main()
