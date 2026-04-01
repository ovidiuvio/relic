#!/usr/bin/env python3
"""
Cloudflare R2 storage for benchmark history.

Uploads and downloads benchmark results to/from R2 bucket, organized by branch.

Usage:
    # Upload benchmark results
    python3 scripts/r2_benchmark_storage.py upload --file results.json --branch main --git-hash abc1234

    # Download benchmark history for a branch
    python3 scripts/r2_benchmark_storage.py download --branch main --output-dir benchmark-history/
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    print("⚠️  boto3 not installed. Install with: pip install boto3")


def get_r2_client():
    """Create R2 S3 client from environment variables."""
    if not HAS_BOTO3:
        return None

    endpoint_url = Path("R2_ENDPOINT").read_text().strip() if Path("R2_ENDPOINT").exists() else ""
    access_key = Path("R2_ACCESS_KEY").read_text().strip() if Path("R2_ACCESS_KEY").exists() else ""
    secret_key = Path("R2_SECRET_KEY").read_text().strip() if Path("R2_SECRET_KEY").exists() else ""
    bucket_name = Path("R2_BUCKET_NAME").read_text().strip() if Path("R2_BUCKET_NAME").exists() else "relic-benchmarks"
    region = Path("R2_REGION").read_text().strip() if Path("R2_REGION").exists() else "auto"

    # Also check environment variables
    import os
    endpoint_url = endpoint_url or os.environ.get("R2_ENDPOINT", "")
    access_key = access_key or os.environ.get("R2_ACCESS_KEY", "")
    secret_key = secret_key or os.environ.get("R2_SECRET_KEY", "")
    bucket_name = bucket_name or os.environ.get("R2_BUCKET_NAME", "relic-benchmarks")
    region = region or os.environ.get("R2_REGION", "auto")

    if not all([endpoint_url, access_key, secret_key]):
        print("❌ R2 credentials not configured. Set R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY")
        return None

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    ), bucket_name


def upload_result(file_path: Path, branch: str, git_hash: str, runner_id: str | None = None) -> bool:
    """Upload benchmark result to R2."""
    result = get_r2_client()
    if not result or result[0] is None:
        return False
    
    r2_client, bucket_name = result

    # Organize by branch: benchmarks/{branch}/{git_hash}.json
    key = f"benchmarks/{branch}/{git_hash}.json"

    try:
        # Load, add runner_id metadata, then upload
        with open(file_path, "r") as f:
            data = json.load(f)

        # Add runner_id to metadata if provided
        if runner_id:
            if "_metadata" not in data:
                data["_metadata"] = {}
            data["_metadata"]["runner_id"] = runner_id
            print(f"📝 Added runner_id: {runner_id}")

        # Upload modified JSON
        import io
        json_bytes = io.BytesIO(json.dumps(data, indent=2).encode("utf-8"))
        r2_client.upload_fileobj(json_bytes, bucket_name, key)
        print(f"✅ Uploaded to R2: s3://{bucket_name}/{key}")
        return True
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False


def download_history(branch: str, output_dir: Path) -> list[Path]:
    """Download all benchmark results for a branch from R2."""
    result = get_r2_client()
    if not result or result[0] is None:
        return []
    
    r2_client, bucket_name = result

    prefix = f"benchmarks/{branch}/"
    downloaded = []

    try:
        response = r2_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if "Contents" not in response:
            print(f"⚠️  No benchmark history found for branch: {branch}")
            return []

        output_dir.mkdir(parents=True, exist_ok=True)

        for obj in response["Contents"]:
            key = obj["Key"]
            if not key.endswith(".json"):
                continue

            # Extract git hash from key: benchmarks/{branch}/{git_hash}.json
            git_hash = key.split("/")[-1].replace(".json", "")
            output_path = output_dir / f"results-{git_hash}.json"

            r2_client.download_file(bucket_name, key, str(output_path))
            downloaded.append(output_path)
            print(f"✅ Downloaded: {key} -> {output_path}")

        print(f"✅ Downloaded {len(downloaded)} benchmark files from R2")
        return downloaded

    except Exception as e:
        print(f"❌ Download failed: {e}")
        return []


def download_latest(branch: str, output_path: Path, limit: int = 30) -> bool:
    """Download latest benchmark results for a branch from R2."""
    result = get_r2_client()
    if not result or result[0] is None:
        return False
    
    r2_client, bucket_name = result

    prefix = f"benchmarks/{branch}/"

    try:
        response = r2_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            MaxKeys=limit
        )

        if "Contents" not in response:
            print(f"⚠️  No benchmark history found for branch: {branch}")
            return False

        # Get the latest N files (sorted by LastModified)
        objects = sorted(response["Contents"], key=lambda x: x["LastModified"], reverse=True)[:limit]

        output_path.mkdir(parents=True, exist_ok=True)

        for obj in objects:
            key = obj["Key"]
            if not key.endswith(".json"):
                continue

            git_hash = key.split("/")[-1].replace(".json", "")
            file_output = output_path / f"results-{git_hash}.json"

            r2_client.download_file(bucket_name, key, str(file_output))
            print(f"✅ Downloaded: {key}")

        return True

    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="R2 Benchmark Storage")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload benchmark result to R2")
    upload_parser.add_argument("--file", type=Path, required=True, help="JSON file to upload")
    upload_parser.add_argument("--branch", type=str, required=True, help="Branch name")
    upload_parser.add_argument("--git-hash", type=str, required=True, help="Git commit hash")
    upload_parser.add_argument("--runner-id", type=str, required=False, help="Runner ID (optional)")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download benchmark history from R2")
    download_parser.add_argument("--branch", type=str, required=True, help="Branch name")
    download_parser.add_argument("--output-dir", type=Path, required=True, help="Output directory")
    download_parser.add_argument("--limit", type=int, default=30, help="Max files to download")

    args = parser.parse_args()

    if args.command == "upload":
        if not args.file.exists():
            print(f"❌ File not found: {args.file}")
            sys.exit(1)
        success = upload_result(args.file, args.branch, args.git_hash, args.runner_id)
        sys.exit(0 if success else 1)

    elif args.command == "download":
        downloaded = download_latest(args.branch, args.output_dir, args.limit)
        sys.exit(0 if downloaded else 1)


if __name__ == "__main__":
    main()
