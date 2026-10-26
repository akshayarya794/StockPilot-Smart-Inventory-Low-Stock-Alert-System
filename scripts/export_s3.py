"""
StockPilot — Inventory CSV Export and Optional AWS S3 Backup Utility
PRD Alignment: Section 3, Section 5.2, and Section 9.
"""

import argparse
import datetime
import os
import sys
import requests

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def export_inventory_csv(
    base_url: str = "http://127.0.0.1:5000",
    output_path: str = None,
    s3_bucket: str = None,
    s3_region: str = "us-east-1",
    s3_key: str = None,
):
    print("==================================================")
    print("      StockPilot CSV Export & S3 Backup Tool      ")
    print("==================================================")

    # 1. Fetch CSV from FastAPI endpoint
    csv_url = f"{base_url}/api/export/csv"
    print(f"\n[1] Fetching live inventory snapshot from: {csv_url}")
    try:
        resp = requests.get(csv_url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"ERROR: Failed to download CSV from {csv_url}: {e}")
        sys.exit(1)

    csv_data = resp.text
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 2. Save locally
    if not output_path:
        local_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(local_dir, exist_ok=True)
        output_path = os.path.join(local_dir, f"stockpilot_inventory_{timestamp}.csv")

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        f.write(csv_data)

    print(f" [PASS] Successfully exported local CSV ({len(csv_data)} bytes):")
    print(f"        -> {output_path}")

    # 3. Optional AWS S3 Upload
    bucket_name = s3_bucket or os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        print("\n[2] AWS S3 Backup: SKIPPED (No S3 bucket specified)")
        print("    To upload backups to Amazon S3, set the following environment variables or CLI flags:")
        print("      $env:S3_BUCKET_NAME='my-stockpilot-backup-bucket'")
        print("      $env:AWS_ACCESS_KEY_ID='...'")
        print("      $env:AWS_SECRET_ACCESS_KEY='...'")
        print("    Or run:")
        print("      python scripts/export_s3.py --bucket my-stockpilot-backup-bucket")
        return output_path

    print(f"\n[2] Uploading backup to Amazon S3 bucket '{bucket_name}'...")
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        target_key = s3_key or f"backups/stockpilot_inventory_{timestamp}.csv"
        region = s3_region or os.getenv("AWS_REGION", "us-east-1")

        s3_client = boto3.client("s3", region_name=region)
        s3_client.upload_file(output_path, bucket_name, target_key)
        
        s3_uri = f"s3://{bucket_name}/{target_key}"
        print(f" [PASS] Successfully uploaded to Amazon S3: {s3_uri}")
        return s3_uri

    except ImportError:
        print("  WARNING: boto3 package is not installed. Install via: pip install boto3")
    except (BotoCoreError, ClientError) as err:
        print(f"  AWS S3 Upload Error: {err}")
        print("  Ensure your AWS IAM role or credentials have s3:PutObject permissions.")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Export StockPilot inventory to CSV and optionally upload to AWS S3")
    parser.add_argument("--url", default="http://127.0.0.1:5000", help="Base URL of StockPilot API (default: http://127.0.0.1:5000)")
    parser.add_argument("--output", default=None, help="Local file path for exported CSV")
    parser.add_argument("--bucket", default=None, help="Target AWS S3 bucket name")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--key", default=None, help="Target S3 object key prefix")

    args = parser.parse_args()
    export_inventory_csv(
        base_url=args.url,
        output_path=args.output,
        s3_bucket=args.bucket,
        s3_region=args.region,
        s3_key=args.key,
    )


if __name__ == "__main__":
    main()
