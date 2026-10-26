import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def verify_docker_configs():
    print("==================================================")
    print("      StockPilot Phase 4 Verification Suite       ")
    print("==================================================")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dockerfile_path = os.path.join(base_dir, "Dockerfile")
    compose_path = os.path.join(base_dir, "docker-compose.yml")
    dockerignore_path = os.path.join(base_dir, ".dockerignore")

    # 1. Verify .dockerignore
    print("\n--- Step 1: Validating .dockerignore ---")
    assert os.path.exists(dockerignore_path), ".dockerignore missing!"
    with open(dockerignore_path, "r", encoding="utf-8") as f:
        dockerignore_content = f.read()
    
    assert "venv/" in dockerignore_content, ".dockerignore must ignore venv/"
    assert "__pycache__/" in dockerignore_content, ".dockerignore must ignore __pycache__/"
    assert "data/*.db" in dockerignore_content, ".dockerignore must ignore local database files"
    print(" [PASS] .dockerignore correctly excludes venv, pycache, and local DB files.")

    # 2. Verify Dockerfile
    print("\n--- Step 2: Validating Dockerfile Syntax & PRD Section 7.1 Directives ---")
    assert os.path.exists(dockerfile_path), "Dockerfile missing!"
    with open(dockerfile_path, "r", encoding="utf-8") as f:
        dockerfile_content = f.read()

    required_dockerfile_rules = [
        ("Base image python:3.11-slim", "FROM python:3.11-slim"),
        ("Working directory /app", "WORKDIR /app"),
        ("Data directory /app/data", "RUN mkdir -p /app/data"),
        ("Environment DB_PATH", "DB_PATH=/app/data/stockpilot.db"),
        ("Environment PORT=5000", "PORT=5000"),
        ("Expose port 5000", "EXPOSE 5000"),
        ("Native Docker HEALTHCHECK", "HEALTHCHECK"),
        ("Healthcheck URL /health", "http://localhost:5000/health"),
        ("Uvicorn CMD on port 5000", 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]'),
    ]

    for label, pattern in required_dockerfile_rules:
        assert pattern in dockerfile_content, f"Dockerfile missing requirement: {label} (pattern: '{pattern}')"
        print(f" [PASS] Dockerfile verified: {label}")

    # 3. Verify docker-compose.yml
    print("\n--- Step 3: Validating docker-compose.yml Structure ---")
    assert os.path.exists(compose_path), "docker-compose.yml missing!"
    with open(compose_path, "r", encoding="utf-8") as f:
        compose_content = f.read()

    required_compose_rules = [
        ("Port mapping 5000:5000", '"5000:5000"'),
        ("Named volume stockpilot-data:/app/data", "stockpilot-data:/app/data"),
        ("Named volume definition", "stockpilot-data:"),
        ("Container name stockpilot-app", "container_name: stockpilot-app"),
    ]

    for label, pattern in required_compose_rules:
        assert pattern in compose_content, f"docker-compose.yml missing: {label}"
        print(f" [PASS] docker-compose verified: {label}")

    print("\n==================================================")
    print(" >>> ALL PHASE 4 CONFIGURATIONS VERIFIED! <<<     ")
    print("==================================================")


if __name__ == "__main__":
    verify_docker_configs()
