#!/usr/bin/env python3
"""
Simple data upload script for Azure ML Sentiment Analysis

Loads JSON data from file and uploads to Azure Blob Storage using DefaultAzureCredential.
Automatically manages permissions by adding Storage Blob Data Contributor role before upload
and removing it afterwards for security.
"""

import os
import sys
import json
import subprocess
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

# Get script directory and project root for proper path resolution
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Import environment utilities using absolute path
sys.path.append(os.path.join(project_root, 'src'))
from env_utils import get_env

def get_current_user_email():
    """Get the current Azure user's email address."""
    try:
        result = subprocess.run(['az', 'account', 'show', '--query', 'user.name', '-o', 'tsv'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get current user: {e}")
        return None

def add_storage_permission(user_email, subscription_id, resource_group, storage_account):
    """Add Storage Blob Data Contributor permission to the current user."""
    scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Storage/storageAccounts/{storage_account}"
    
    try:
        print(f"🔐 Adding Storage Blob Data Contributor permission...")
        result = subprocess.run([
            'az', 'role', 'assignment', 'create',
            '--assignee', user_email,
            '--role', 'Storage Blob Data Contributor',
            '--scope', scope
        ], capture_output=True, text=True, check=True)
        
        print(f"✓ Permission added successfully")
        return True
    except subprocess.CalledProcessError as e:
        if "RoleAssignmentExists" in e.stderr:
            print(f"✓ Permission already exists")
            return True
        else:
            print(f"❌ Failed to add permission: {e.stderr}")
            return False

def remove_storage_permission(user_email, subscription_id, resource_group, storage_account):
    """Remove Storage Blob Data Contributor permission from the current user."""
    scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Storage/storageAccounts/{storage_account}"
    
    try:
        print(f"🔐 Removing Storage Blob Data Contributor permission...")
        result = subprocess.run([
            'az', 'role', 'assignment', 'delete',
            '--assignee', user_email,
            '--role', 'Storage Blob Data Contributor',
            '--scope', scope
        ], capture_output=True, text=True, check=True)
        
        print(f"✓ Permission removed successfully")
        return True
    except subprocess.CalledProcessError as e:
        if "RoleAssignmentNotFound" in e.stderr:
            print(f"✓ Permission was already removed")
            return True
        else:
            print(f"⚠️  Failed to remove permission: {e.stderr}")
            return False

def main():
    """Main function to upload data with automatic permission management."""
    
    # Get configuration from environment variables
    storage_account_name = get_env('AZURE_STORAGE_ACCOUNT_NAME')
    container_name = get_env('STORAGE_CONTAINER_NAME', 'data')
    file_name = get_env('INPUT_DATA_FILE', 'sample_sentiment_data.json')
    subscription_id = get_env('AZURE_SUBSCRIPTION_ID')
    resource_group = get_env('AZURE_RESOURCE_GROUP_NAME')

    # Validate required environment variables
    required_vars = {
        'AZURE_STORAGE_ACCOUNT_NAME': storage_account_name,
        'AZURE_SUBSCRIPTION_ID': subscription_id,
        'AZURE_RESOURCE_GROUP_NAME': resource_group
    }
    
    for var_name, var_value in required_vars.items():
        if not var_value:
            print(f"Error: {var_name} environment variable is not set.")
            print("Please ensure your .env.local file contains all required values.")
            sys.exit(1)

    print(f"✓ Using storage account: {storage_account_name}")
    print(f"✓ Using resource group: {resource_group}")
    print(f"✓ Using subscription: {subscription_id}")
    print("✓ Using DefaultAzureCredential (same as az login)")

    # Calculate absolute path to data file
    data_file_path = os.path.join(project_root, 'data', file_name)

    print(f"Script directory: {script_dir}")
    print(f"Project root: {project_root}")
    print(f"Data file path: {data_file_path}")

    # Load data from JSON file
    try:
        with open(data_file_path, 'r') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data)} records from {data_file_path}")
    except FileNotFoundError:
        print(f"Error: Data file '{data_file_path}' not found.")
        print(f"Please ensure the file exists or set the INPUT_DATA_FILE environment variable.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{data_file_path}': {e}")
        sys.exit(1)

    # Get current user email
    user_email = get_current_user_email()
    if not user_email:
        print("❌ Could not determine current user. Please ensure you are logged in with 'az login'.")
        sys.exit(1)
    
    print(f"✓ Current user: {user_email}")

    # Add storage permission
    permission_added = add_storage_permission(user_email, subscription_id, resource_group, storage_account_name)
    if not permission_added:
        print("❌ Failed to add required permissions. Upload cannot proceed.")
        sys.exit(1)

    try:
        # Create blob service client using DefaultAzureCredential (same as az login)
        credential = DefaultAzureCredential()
        account_url = f"https://{storage_account_name}.blob.core.windows.net"

        print(f"✓ Connecting to: {account_url}")

        try:
            blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
            container_client = blob_service_client.get_container_client(container_name)
            print("✓ Successfully authenticated with Azure using az login credentials")
        except Exception as e:
            print(f"❌ Failed to authenticate with Azure: {str(e)}")
            print("Please ensure you are logged in with 'az login' and have access to the storage account.")
            raise

        # Create container if it doesn't exist
        try:
            print(f"✓ Creating container '{container_name}'")
            container_client.create_container()
            print(f"✓ Created container '{container_name}'")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                print(f"✓ Container '{container_name}' already exists")
            else:
                print(f"Error creating container: {e}")
                raise

        # Upload JSON data to blob
        try:
            blob_client = container_client.get_blob_client(file_name)
            blob_client.upload_blob(json.dumps(data), overwrite=True)
            print(f"✓ Uploaded {file_name} to container '{container_name}'")
            print("✅ Upload completed successfully!")
        except Exception as e:
            print(f"❌ Failed to upload data: {str(e)}")
            print("Please check your permissions and ensure the storage account is accessible.")
            raise

    finally:
        # Always try to remove the permission, even if upload failed
        print("\n🔐 Cleaning up permissions...")
        remove_storage_permission(user_email, subscription_id, resource_group, storage_account_name)
        print("✅ Permission cleanup completed!")

if __name__ == "__main__":
    main()
