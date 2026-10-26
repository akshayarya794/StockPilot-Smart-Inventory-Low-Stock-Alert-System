import subprocess
import sys
import time
import requests

SERVER_URL = "http://127.0.0.1:5000"


def wait_for_server(timeout_sec: int = 15):
    """Wait for the Uvicorn server to become available."""
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            resp = requests.get(f"{SERVER_URL}/health", timeout=1)
            if resp.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    return False


def run_verification():
    print("==================================================")
    print("      StockPilot Phase 2 Verification Suite       ")
    print("==================================================")

    # 1. Start Uvicorn process
    print("\n[Step 1] Starting Uvicorn on 0.0.0.0:5000...")
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "5000"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        is_ready = wait_for_server()
        if not is_ready:
            print("ERROR: Uvicorn server failed to start within timeout.")
            stdout, stderr = proc.communicate(timeout=2)
            print("Server stdout:", stdout.decode())
            print("Server stderr:", stderr.decode())
            sys.exit(1)

        print("Uvicorn server is UP and responding.")

        # Test 1: GET /health
        print("\n--- Test 1: Health Check (GET /health) ---")
        health_resp = requests.get(f"{SERVER_URL}/health")
        print(f"Status Code: {health_resp.status_code}")
        health_data = health_resp.json()
        print(f"Response: {health_data}")
        assert health_resp.status_code == 200, "Health check must return 200 OK"
        assert health_data["status"] == "ok"
        assert health_data["database"] == "connected"
        print(">>> Test 1 PASSED: /health returned 200 OK & database is connected.")

        # Test 2: GET /api/products
        print("\n--- Test 2: List Products (GET /api/products) ---")
        products_resp = requests.get(f"{SERVER_URL}/api/products")
        print(f"Status Code: {products_resp.status_code}")
        products_data = products_resp.json()
        summary = products_data["summary"]
        items = products_data["items"]
        print(f"Summary Metrics: {summary}")
        print(f"Seeded Products Count: {len(items)}")
        for item in items:
            badge = "LOW STOCK" if item["is_low_stock"] else "IN STOCK"
            print(f" - [{item['sku']}] {item['name']} | Qty: {item['quantity']} | {badge}")

        assert products_resp.status_code == 200, "Products list must return 200 OK"
        assert summary["total_products"] == 6, f"Expected 6 products, got {summary['total_products']}"
        assert summary["low_stock_count"] == 3, f"Expected 3 low stock, got {summary['low_stock_count']}"
        assert len(items) == 6, f"Expected 6 items in list, got {len(items)}"
        print(">>> Test 2 PASSED: 6 seeded items and summary metrics verified.")

        # Test 3: Negative stock prevention on PATCH & POST /api/products/{id}/stock
        print("\n--- Test 3: Negative Stock Prevention (PATCH /api/products/{id}/stock) ---")
        first_product_id = items[0]["id"]
        current_qty = items[0]["quantity"]
        excessive_reduction = -(current_qty + 10)
        stock_resp = requests.patch(
            f"{SERVER_URL}/api/products/{first_product_id}/stock",
            json={"delta": excessive_reduction},
        )
        print(f"Attempted delta: {excessive_reduction} on current qty {current_qty}")
        print(f"Status Code: {stock_resp.status_code}")
        print(f"Response: {stock_resp.json()}")
        assert stock_resp.status_code == 400, "Reducing stock below 0 must return HTTP 400"
        assert "negative" in stock_resp.json()["detail"].lower()
        print(">>> Test 3 PASSED: Negative stock reduction strictly rejected with HTTP 400.")

        # Test 4: Duplicate SKU prevention on POST /api/products
        print("\n--- Test 4: Duplicate SKU Prevention (POST /api/products) ---")
        existing_sku = items[0]["sku"]
        duplicate_payload = {
            "name": "Duplicate Test Item",
            "category": "Electronics",
            "sku": existing_sku,
            "quantity": 10,
            "reorder_level": 5,
        }
        dup_resp = requests.post(f"{SERVER_URL}/api/products", json=duplicate_payload)
        print(f"Attempted creating duplicate SKU: '{existing_sku}'")
        print(f"Status Code: {dup_resp.status_code}")
        print(f"Response: {dup_resp.json()}")
        assert dup_resp.status_code == 409, "Duplicate SKU must return HTTP 409 Conflict"
        print(">>> Test 4 PASSED: Duplicate SKU strictly rejected with HTTP 409 Conflict.")

        # Test 5: CSV Export (GET /api/export/csv)
        print("\n--- Test 5: CSV Export (GET /api/export/csv) ---")
        csv_resp = requests.get(f"{SERVER_URL}/api/export/csv")
        print(f"Status Code: {csv_resp.status_code}")
        print(f"Content-Type: {csv_resp.headers.get('Content-Type')}")
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers.get("Content-Type", "")
        csv_lines = csv_resp.text.strip().splitlines()
        print(f"CSV Header: {csv_lines[0]}")
        print(f"Exported rows count (including header): {len(csv_lines)}")
        assert len(csv_lines) == 7, "CSV must contain header + 6 products"
        print(">>> Test 5 PASSED: CSV export generated successfully.")

        # Test 6: Filtering by low_stock_only
        print("\n--- Test 6: Low-Stock Filter (GET /api/products?low_stock_only=true) ---")
        filter_resp = requests.get(f"{SERVER_URL}/api/products?low_stock_only=true")
        filtered_items = filter_resp.json()["items"]
        print(f"Filtered low-stock items returned: {len(filtered_items)}")
        for fi in filtered_items:
            assert fi["is_low_stock"] is True
            print(f" - [{fi['sku']}] {fi['name']} (Qty: {fi['quantity']} <= Reorder: {fi['reorder_level']})")
        assert len(filtered_items) == 3
        print(">>> Test 6 PASSED: Low-stock filter correctly isolates 3 items.")

        print("\n==================================================")
        print(" >>> ALL PHASE 2 VERIFICATION TESTS PASSED! <<<   ")
        print("==================================================")

    finally:
        print("\nShutting down temporary Uvicorn process...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Uvicorn process stopped.")


if __name__ == "__main__":
    run_verification()
