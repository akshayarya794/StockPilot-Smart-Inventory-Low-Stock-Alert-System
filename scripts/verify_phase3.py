import subprocess
import sys
import time
import requests

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
    print("      StockPilot Phase 3 Verification Suite       ")
    print("==================================================")

    # 1. Start Uvicorn process using current python (venv)
    print("\n[Step 1] Starting Uvicorn on 127.0.0.1:5000 via virtual environment...")
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

        # Test 1: GET / (Dashboard UI rendering)
        print("\n--- Test 1: Render Dashboard UI (GET /) ---")
        dash_resp = requests.get(f"{SERVER_URL}/")
        print(f"Status Code: {dash_resp.status_code}")
        print(f"Content-Type: {dash_resp.headers.get('Content-Type')}")
        assert dash_resp.status_code == 200, "Dashboard must return HTTP 200 OK"
        assert "text/html" in dash_resp.headers.get("Content-Type", "")

        html = dash_resp.text
        print(f"Rendered HTML length: {len(html)} bytes")

        # Test 2: Check Required UI Elements
        print("\n--- Test 2: Verify UI Component Elements ---")
        required_elements = [
            ("Branding Header", "StockPilot"),
            ("Health Badge Container", 'id="health-badge-container"'),
            ("Total Products KPI Card", 'id="kpi-total-products"'),
            ("Total Units KPI Card", 'id="kpi-total-units"'),
            ("Low-Stock Alerts KPI Card", 'id="kpi-low-stock"'),
            ("Global Alert Banner", 'id="global-alert-banner"'),
            ("Search Input", 'id="search-input"'),
            ("Low-Stock Toggle Switch", 'id="low-stock-toggle"'),
            ("Inventory Table Body", 'id="inventory-table-body"'),
            ("Add Product Modal", 'id="add-product-modal"'),
            ("Edit Product Modal", 'id="edit-product-modal"'),
            ("Toast Container", 'id="toast-container"'),
            ("Health Polling Script", 'fetch("/health")'),
            ("Products Fetch Script", 'fetch(url)'),
            ("Export CSV Link", 'href="/api/export/csv"'),
            ("Swagger Docs Link", 'href="/docs"'),
        ]

        for name, pattern in required_elements:
            assert pattern in html, f"Missing required element: {name} (Pattern: {pattern})"
            print(f" \u2714 Verified: {name}")

        # Test 3: Verify Static Assets (GET /static/style.css)
        print("\n--- Test 3: Static Asset Serving (GET /static/style.css) ---")
        css_resp = requests.get(f"{SERVER_URL}/static/style.css")
        print(f"Status Code: {css_resp.status_code}")
        print(f"Content-Type: {css_resp.headers.get('Content-Type')}")
        assert css_resp.status_code == 200, "Static CSS must return HTTP 200"
        assert "glass-panel" in css_resp.text
        print(" \u2714 Verified: Static CSS is served properly with custom styles")

        print("\n==================================================")
        print(" >>> ALL PHASE 3 VERIFICATION TESTS PASSED! <<<   ")
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
