#!/usr/bin/env python3
"""
Destroy the Alex Financial Advisor Part 7 infrastructure.
This script:
1. Empties the S3 bucket
2. Destroys infrastructure with Terraform
3. Cleans up local artifacts
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None, check=True, capture_output=False):
    """Run a command and optionally capture output."""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    if capture_output:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=isinstance(cmd, str))
        if check and result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None
        return result.stdout.strip()
    else:
        result = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str))
        if check and result.returncode != 0:
            return False
        return True


def confirm_destruction():
    """Ask for confirmation before destroying resources."""
    print("⚠️  WARNING: This will destroy all Part 7 infrastructure!")
    print("This includes:")
    print("  - CloudFront distribution")
    print("  - API Gateway")
    print("  - Lambda function")
    print("  - S3 bucket and all contents")
    print("  - IAM roles and policies")
    print("")

    response = input("Are you sure you want to continue? Type 'yes' to confirm: ")
    return response.lower() == 'yes'


def get_bucket_name():
    """Get the S3 bucket name from Terraform output."""
    terraform_dir = Path(__file__).parent.parent / "terraform" / "7_frontend"

    if not terraform_dir.exists():
        print(f"  ❌ Terraform directory not found: {terraform_dir}")
        return None

    # Get the bucket name from Terraform
    bucket_output = run_command(
        ["terraform", "output", "-raw", "s3_bucket_name"],
        cwd=terraform_dir,
        capture_output=True
    )

    return bucket_output if bucket_output else None


def empty_s3_bucket(bucket_name):
    """Empty the S3 bucket before deletion."""
    if not bucket_name:
        print("  ⚠️  No bucket name provided, skipping...")
        return

    print(f"\n🗑️  Emptying S3 bucket: {bucket_name}")

    # Check if bucket exists
    exists = run_command(
        ["aws", "s3", "ls", f"s3://{bucket_name}"],
        capture_output=True,
        check=False
    )

    if not exists:
        print(f"  Bucket {bucket_name} doesn't exist or is already empty")
        return

    # Delete all objects and versions using rb --force
    print(f"  Force deleting all objects and versions from {bucket_name}...")
    run_command([
        "aws", "s3", "rb",
        f"s3://{bucket_name}/",
        "--force"
    ], check=False)

    print(f"  ✅ Bucket {bucket_name} emptied")


def destroy_terraform():
    """Destroy infrastructure with Terraform."""
    print("\n🏗️  Destroying infrastructure with Terraform...")

    terraform_dir = Path(__file__).parent.parent / "terraform" / "7_frontend"

    if not terraform_dir.exists():
        print(f"  ❌ Terraform directory not found: {terraform_dir}")
        return False

    # Check if Terraform is initialized
    if not (terraform_dir / ".terraform").exists():
        print("  ⚠️  Terraform not initialized, nothing to destroy")
        return True

    # Destroy the infrastructure
    print("  Running terraform destroy...")
    print("  Type 'yes' when prompted to confirm destruction.")

    success = run_command(["terraform", "destroy"], cwd=terraform_dir)

    if success:
        print("  ✅ Infrastructure destroyed successfully")
    else:
        print("  ❌ Failed to destroy infrastructure")
        print("  You may need to manually clean up resources in AWS Console")

    return success


def clean_local_artifacts():
    """Clean up local build artifacts."""
    print("\n🧹 Cleaning up local artifacts...")

    artifacts = [
        Path(__file__).parent.parent / "backend" / "api" / "api_lambda.zip",
        Path(__file__).parent.parent / "frontend" / "out",
        Path(__file__).parent.parent / "frontend" / ".next",
    ]

    for artifact in artifacts:
        if artifact.exists():
            if artifact.is_file():
                artifact.unlink()
                print(f"  Deleted: {artifact}")
            else:
                import shutil
                shutil.rmtree(artifact)
                print(f"  Deleted directory: {artifact}")

    print("  ✅ Local artifacts cleaned")


def empty_all_buckets():
    """Empty all Alex S3 buckets."""
    print("\n🗑️  Finding and emptying all Alex S3 buckets...")
    
    # Get AWS account ID
    account_id = run_command(
        ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
        capture_output=True
    )
    
    if not account_id:
        print("  ⚠️  Could not get AWS account ID")
        return
    
    # List of potential Alex buckets
    bucket_patterns = [
        f"alex-frontend-{account_id}",
        f"alex-lambda-packages-{account_id}",
        f"alex-vector-{account_id}"
    ]
    
    for bucket_name in bucket_patterns:
        # Check if bucket exists
        exists = run_command(
            ["aws", "s3", "ls", f"s3://{bucket_name}"],
            capture_output=True,
            check=False
        )
        
        if exists:
            print(f"  Emptying bucket: {bucket_name}")
            run_command([
                "aws", "s3", "rm",
                f"s3://{bucket_name}/",
                "--recursive"
            ], check=False)
            print(f"  ✅ Emptied {bucket_name}")


def main():
    """Main destruction function."""
    print("💥 Alex Financial Advisor - Part 7 Infrastructure Destruction")
    print("=" * 60)

    # Confirm destruction
    if not confirm_destruction():
        print("\n❌ Destruction cancelled")
        sys.exit(0)

    # Empty all Alex S3 buckets
    empty_all_buckets()

    # Destroy Terraform infrastructure
    destroy_terraform()

    # Clean local artifacts
    clean_local_artifacts()

    print("\n" + "=" * 60)
    print("✅ Destruction complete!")
    print("\nTo redeploy, run:")
    print("  uv run scripts/deploy.py")


if __name__ == "__main__":
    main()