# Azure ML Sentiment Analysis Project

A cloud-native sentiment analysis pipeline built on Azure Machine Learning, following Infrastructure as Code (IaC) and MLOps best practices.

## Project Overview

This project demonstrates how to build a scalable, reproducible sentiment analysis solution using:
- **Azure Machine Learning** for ML operations and compute
- **Azure Bicep** for Infrastructure as Code
- **HuggingFace Transformers** for sentiment analysis models
- **Azure Table Storage** for structured sentiment results storage
- **Azure Blob Storage** for data storage and artefacts

## Prerequisites

### 1. Azure Account & Permissions

You need an Azure subscription with the **Contributor** role assigned at either:
- Subscription level (recommended), OR
- Resource group level (minimum)

#### Required Azure RBAC Permissions

The deployment creates multiple Azure resources that require the **Contributor** role, which includes permissions for:
- Key Vault creation and management
- Application Insights components
- Log Analytics workspaces  
- Azure Machine Learning workspaces and compute clusters
- Storage accounts

#### Check Your Current Permissions

Run these Azure CLI commands to verify your permissions:

```bash
# Check role assignments at subscription level
az role assignment list --assignee "your-email@domain.com" --subscription "your-subscription-id" --output table

# Check role assignments at resource group level
az role assignment list --assignee "your-email@domain.com" --resource-group "sentiment-analysis-rg" --output table

# Check all your role assignments
az role assignment list --assignee "your-email@domain.com" --all --output table
```

**Expected Output**: You should see "Contributor" role listed with appropriate scope.

#### Request Permissions

If you don't have sufficient permissions, contact your Azure administrator to request:
- **Role**: Contributor
- **Scope**: Subscription or Resource Group
- **Justification**: Required to deploy Azure ML infrastructure including Key Vault, Application Insights, Log Analytics, and ML compute resources

### 2. Development Tools

- **Azure CLI**: [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Bicep CLI**: Usually installed with Azure CLI
- **Python 3.8+**: For ML pipeline development
- **Git**: For version control

### 3. Azure CLI Setup

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "your-subscription-id"

# Verify your login
az account show
```

## Quick Start

Follow these steps to get the sentiment analysis pipeline running:

### 1. Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd sentiment-analysis-azure-ml

# Setup environment variables
cp .env.local.template .env.local
nano .env.local  # Add your AZURE_SUBSCRIPTION_ID and change the AZURE_STORAGE_ACCOUNT_NAME and AZURE_KEY_VAULT_NAME to something unqiue

# Install dependencies
pip install -r requirements.txt

# Login to Azure
az login

# Select the correct subscription

```

### 2. Deploy Infrastructure

The infrastructure deployment creates all Azure resources with proper managed identity configuration:

```bash
# Deploy all infrastructure resources
./scripts/01-deploy-infrastructure.sh
```

This script:
- Creates all Azure resources automatically
- Configures managed identities with proper RBAC roles
- Eliminates the need for manual ML workspace creation
- Sets up security best practices

### 3. Upload the json Data to blob

This will upload the ./data/INPUT_DATA_FILE to blob storage. The script automatically manages permissions by temporarily adding the required Storage Blob Data Contributor role and removing it after upload for security.

```bash
# Upload sample data to Azure Storage (handles permissions automatically)
python scripts/02-upload-data.py
```

### 4. Run the Pipeline

This step will dynamically create a pipeline.yaml file with the correct environment variables as "./pipielines/sentiment_pipeline.yml.generated".

It will then push the pipeline to Azure ML Studio, which will create a container to host the environment

The pipeline will then execute ./scr/sentiment_table.py which will run sentiment analysis over the uploaded json file and write the results to a storage table called SentimentResults


```bash
# Submit and monitor the ML pipeline
python scripts/03-run-pipeline.py
```

### 5. Monitor Results

View progress in:
- Terminal output from the pipeline script
- Azure ML Studio: [https://ml.azure.com](https://ml.azure.com)
- Select your workspace: `senitment-analysis-workgroup`
- Observe the job
- The first run take around 15 mins while the environment is built
- Subsequent runs take around 5 mins

### Optional Scripts

```bash
# Resolve environment placeholders (if needed for troubleshooting)
python scripts/00-resolve-environment.py

# Validate environment configuration
python scripts/validate_environment.py --verbose

# Clean up resources (when finished)
./scripts/99-cleanup-resources.sh
```

## Infrastructure Deployment Details



### Default Configuration

Default values in the .env file

| Resource | Default Name/Configuration |
|----------|---------------------------|
| Resource Group | `sentiment-analysis-rg` |
| Location | `uksouth` |
| Storage Account | `sentstore0001` Must be changed |
| Key Vault | `sentkv0001` Must be changed |
| ML Workspace | `senitment-analysis-workgroup` |
| Compute Cluster | `sentiment-cluster` |
| VM Size | `STANDARD_DS3_V2` |
| Auto-scaling | 0-2 nodes |



## Project Structure

```
sentiment-analysis-azure-ml/
├── README.md                          # This file
├── .env                               # Environment configuration template
├── .gitignore                         # Git ignore file
├── environment.yml                    # Conda environment (sentiment)
├── requirements.txt                   # Python dependencies
├── scripts/                           # Execution scripts (run in order)
│   ├── 00-resolve-environment.py     # Resolve environment placeholders
│   ├── 01-deploy-infrastructure.sh   # Deploy Azure infrastructure
│   ├── 02-upload-data.py             # Upload sample data to storage
│   ├── 03-run-pipeline.py            # Submit and monitor ML pipeline
│   ├── 99-cleanup-resources.sh       # Clean up existing resources (optional)
│   └── validate_environment.py       # Validate environment configuration
├── bicep/                             # Infrastructure as Code
│   ├── main-complete.bicep            # Main Bicep template
│   └── modules/
│       └── complete-infrastructure.bicep # Complete resource definitions
├── src/                               # ML Pipeline Source Code
│   ├── sentiment_table.py             # Sentiment analysis script with Table Storage
│   └── env_utils.py                   # Environment utilities with placeholder support
├── pipelines/                         # Azure ML Pipeline Definitions
│   └── sentiment_pipeline.yml.template # Pipeline configuration template
├── docs/                              # Documentation
│   └── ENVIRONMENT_CONFIGURATION.md   # Environment setup guide
└── data/                              # Sample data
    └── sample_sentiment_data.json     # Sample sentiment data
```

## Architecture

The solution follows Azure Well-Architected Framework principles:

### Core Components
- **Resource Group**: Logical container for all resources
- **Storage Account**: Data lake for raw and processed data with security best practices
- **Azure ML Workspace**: Central hub for ML operations with system-assigned managed identity
- **Compute Cluster**: Auto-scaling compute for ML workloads with system-assigned managed identity

### Security & Monitoring
- **Key Vault**: Secure credential storage with RBAC authorization
- **Application Insights**: Application performance monitoring
- **Log Analytics**: Centralised logging and analytics

### Managed Identity Permissions

#### ML Workspace Managed Identity
- **Storage Blob Data Contributor** - Read/write access to blob data
- **Storage Account Contributor** - Manage storage containers
- **Key Vault Secrets User** - Access secrets in Key Vault

#### Compute Cluster Managed Identity
- **Storage Blob Data Contributor** - Read/write access to blob data
- **Storage Account Contributor** - Manage storage containers
- **Key Vault Secrets User** - Access secrets in Key Vault

### Key Features
- **Auto-scaling**: Compute scales from 0-2 nodes based on demand
- **Cost Optimisation**: Pay-per-use model with automatic scale-down
- **Security**: Encryption at rest and in transit, RBAC controls, managed identities
- **Monitoring**: Comprehensive logging and telemetry

## Troubleshooting

### Common Permission Errors

If you encounter deployment errors like:
```
Authorization failed for template resource 'kv-xxxxx' of type 'Microsoft.KeyVault/vaults'
```

**Solution**: Verify you have Contributor role using the permission check commands above.

### Infrastructure Deployment Issues

1. **Permission Errors**: Ensure you have Contributor or Owner role on the subscription
2. **Resource Name Conflicts**: Storage account names must be globally unique
3. **Location Availability**: Ensure all services are available in your chosen region
4. **Role Assignment Conflicts**: If you get "RoleAssignmentExists" errors:
   - Use `./scripts/99-cleanup-resources.sh` to remove existing resources
   - Or manually delete conflicting role assignments in Azure Portal
   - The template now uses more unique GUIDs to avoid conflicts

### Validation

Before deployment, the script validates the Bicep template to catch errors early.

### Storage Account Name Conflicts

Storage account names must be globally unique. The template uses `uniqueString()` to generate unique names automatically.

### Region Availability

Not all Azure services are available in all regions. The default region is `uksouth`. To check available regions:

```bash
az account list-locations --output table
```

## Cost Considerations

- **Compute Cluster**: Scales to zero when not in use
- **Storage**: Standard LRS tier for cost efficiency  
- **Monitoring**: Basic tiers for development workloads

Estimated monthly cost for development usage: £20-50 (varies by usage)

## Implementation Status

✅ **Infrastructure**: Unified Bicep deployment with managed identity configuration  
✅ **Data Generation**: Synthetic sentiment data creation  
✅ **ML Environment**: sentiment conda environment with HuggingFace transformers  
✅ **Sentiment Analysis**: Complete processing script with batch support  
✅ **Pipeline Definition**: Azure ML pipeline YAML configuration  
✅ **Orchestration**: Pipeline submission and monitoring script  
✅ **Documentation**: Comprehensive usage guide  
✅ **Security**: Managed identities and RBAC best practices  



## Next Steps

After successful deployment:

1. **Navigate to Azure ML Studio**: [https://ml.azure.com](https://ml.azure.com)
2. **Select your workspace**: `senitment-analysis-workgroup`

## Support

- **Infrastructure Issues**: Review the troubleshooting section above for deployment guidance
- **Permission Problems**: Use the permission check commands above
- **ML Pipeline Issues**: Review Azure ML Studio logs and documentation
- **General Questions**: Refer to the PROJECT_SUMMARY.md for architecture details



### Script Prerequisites

1. **Azure CLI**: Install and login to Azure
   ```bash
   az login
   ```

2. **Python Dependencies**: Install required packages
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**: Set up your environment file
   ```bash
   cp .env.local.template .env.local
   # Edit .env.local with your Azure subscription ID
   ```



### Script Environment Variables

All scripts use the centralized environment configuration system:
- Configuration loaded from `.env.local` (preferred) or `.env`
- Supports placeholder replacement for globally unique resource names
- See `docs/ENVIRONMENT_CONFIGURATION.md` for detailed documentation

### Script Troubleshooting

- **Script fails**: Check environment variables with `python scripts/validate_environment.py`
- **Azure authentication**: Ensure you're logged in with `az account show`
- **Permissions**: Verify your Azure account has Contributor access to the subscription
- **Resource conflicts**: Use `./scripts/99-cleanup-resources.sh` to clean up existing resources



---

**Note**: This project is designed for educational and development purposes. For production deployments, review and adjust security, networking, and scaling configurations according to your organisation's requirements.
