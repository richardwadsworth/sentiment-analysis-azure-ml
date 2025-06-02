# Environment Configuration Guide

This document explains how to use the environment configuration file (`.env`) that contains all configuration values extracted from the bicep files, shell scripts, and Python files in this Azure ML sentiment analysis project.

## Overview

The `.env` file centralises all configuration values that were previously hardcoded throughout the project files. This approach provides several benefits:

- **Centralised Configuration**: All settings in one place
- **Environment-Specific Deployments**: Easy switching between dev/test/prod
- **Security**: Sensitive values can be managed separately
- **Maintainability**: Changes only need to be made in one location
- **Documentation**: Clear understanding of all configurable parameters

## File Structure

The `.env` file is organised into logical sections:

### 1. Azure Infrastructure Configuration
- Subscription ID, resource group, location
- Resource names (storage account, key vault, ML workspace, compute cluster)
- Resource tags

### 2. Azure Storage Configuration
- Storage account settings (SKU, kind, access tier)
- Security settings (TLS version, public access, HTTPS)
- Container and file names

### 3. Azure Key Vault Configuration
- Key vault SKU and security settings
- Retention policies and RBAC settings

### 4. Azure ML Workspace Configuration
- Workspace settings and authentication mode
- Default datastore configuration

### 5. Azure ML Compute Configuration
- VM size, scaling settings, and network configuration
- Node count and idle time settings

### 6. Monitoring and Logging Configuration
- Log Analytics and Application Insights settings
- Retention periods and monitoring configuration

### 7. ML Model Configuration
- HuggingFace model settings
- Batch processing and text field configuration

### 8. Pipeline Configuration
- Experiment names and pipeline settings
- Monitoring and output configuration

### 9. Runtime Environment Variables
- Python path and cache configurations
- Logging and debugging settings

### 10. Additional Sections
- Development and testing settings
- Security configuration
- Performance optimisation
- Feature flags
- Backup and recovery
- Cost optimisation
- Compliance and governance

## Usage Instructions

### Step 1: Copy and Customise Environment File

```bash
# Copy the template environment file
cp .env .env.local

# Edit the local environment file with your specific values
nano .env.local
```

### Step 2: Set Required Values

At minimum, you must set these values in your `.env.local` file:

```bash
# Required: Your Azure subscription ID
AZURE_SUBSCRIPTION_ID="your-subscription-id-here"
AZURE_STORAGE_ACCOUNT_NAME="yourstorageaccountname"
AZURE_KEY_VAULT_NAME="your-key-vault-name"

# Optional: Customise resource names if needed
AZURE_RESOURCE_GROUP_NAME="your-resource-group-name"
AZURE_ML_WORKSPACE_NAME="your-ml-workspace-name"
```

## Security Best Practices

1. **Never commit sensitive values**: Add `.env.local` to `.gitignore`
2. **Use Azure Key Vault**: Store secrets in Key Vault and reference them
3. **Rotate credentials regularly**: Update connection strings and keys periodically
4. **Use managed identities**: Prefer managed identity over connection strings where possible
5. **Limit access**: Only grant necessary permissions to service principals

## Validation Script

Create a validation script to check environment configuration:

```python
#!/usr/bin/env python3
"""Validate environment configuration"""

import os
from dotenv import load_dotenv

def validate_environment():
    load_dotenv('.env.local')
    load_dotenv('.env')
    
    required_vars = [
        'AZURE_SUBSCRIPTION_ID',
        'AZURE_RESOURCE_GROUP_NAME',
        'AZURE_LOCATION',
        'AZURE_STORAGE_ACCOUNT_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required environment variables are set")
    return True

if __name__ == "__main__":
    validate_environment()
```

## Troubleshooting

### Common Issues

1. **Environment variables not loading**
   - Check file path and permissions
   - Ensure no syntax errors in .env file
   - Verify export command in shell scripts

2. **Values not being used**
   - Check variable names match exactly
   - Ensure environment loading happens before variable usage
   - Verify fallback values are appropriate

3. **Permission errors**
   - Check Azure RBAC roles are assigned correctly
   - Verify managed identity is enabled
   - Ensure Key Vault access policies are configured

### Debug Commands

```bash
# Check if environment variables are loaded
env | grep AZURE_

# Validate bicep template with parameters
az deployment sub validate \
    --location "$AZURE_LOCATION" \
    --template-file bicep/main-complete.bicep \
    --parameters @parameters.json

# Test Azure authentication
az account show
az ml workspace list
```

## Support

For questions or issues with environment configuration:

1. Check this documentation first
2. Validate your environment file syntax
3. Test with minimal configuration
4. Check Azure portal for resource status
5. Review Azure ML studio for pipeline errors

Remember to never commit sensitive configuration values to version control!
