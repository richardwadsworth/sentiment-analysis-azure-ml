#!/bin/bash

# Azure ML Sentiment Analysis - Complete Deployment Script
# This script deploys all resources in one go, including ML workspace with managed identity
# Merged from deploy-01-prerequisites.sh and deploy-02-post-workspace-simple.sh

set -e

# Load environment variables safely
if [ -f .env.local ]; then
    set -a  # automatically export all variables
    source .env.local
    set +a  # stop automatically exporting
elif [ -f .env ]; then
    set -a  # automatically export all variables
    source .env
    set +a  # stop automatically exporting
fi

# Configuration from environment variables
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"
RESOURCE_GROUP_NAME="${AZURE_RESOURCE_GROUP_NAME:-sentiment-analysis-rg}"
LOCATION="${AZURE_LOCATION:-uksouth}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME_PREFIX:-sentiment-complete}-$(date +%Y%m%d-%H%M%S)"

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Azure ML Sentiment Analysis - Complete Deployment${NC}"
echo "=================================================="

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}You are not logged in to Azure. Please log in...${NC}"
    az login
fi

# Get current subscription if not set
if [ -z "$SUBSCRIPTION_ID" ]; then
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    echo -e "${YELLOW}Using current subscription: $SUBSCRIPTION_ID${NC}"
fi

# Set the subscription
az account set --subscription "$SUBSCRIPTION_ID"

echo -e "${GREEN}Deploying complete Azure ML infrastructure...${NC}"
echo "Subscription: $SUBSCRIPTION_ID"
echo "Resource Group: $RESOURCE_GROUP_NAME"
echo "Location: $LOCATION"
echo "Deployment Name: $DEPLOYMENT_NAME"
echo ""

echo -e "${BLUE}📋 What will be deployed:${NC}"
echo "✅ Resource Group"
echo "✅ Storage Account (with security best practices + Table Storage)"
echo "✅ Key Vault (with RBAC enabled)"
echo "✅ Log Analytics Workspace"
echo "✅ Application Insights"
echo "✅ Azure ML Workspace (with system-assigned managed identity)"
echo "✅ Compute Cluster (with system-assigned managed identity, auto-scaling 0-2 nodes)"
echo "✅ RBAC Role Assignments:"
echo "   • ML Workspace → Storage Blob Data Contributor + Key Vault Secrets User"
echo "   • Compute Cluster → Storage Blob Data Contributor + Storage Table Data Contributor + Storage Account Contributor + Key Vault Secrets User"
echo ""

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BICEP_FILE="$PROJECT_ROOT/bicep/main-complete.bicep"

echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo "Bicep file: $BICEP_FILE"

# Check if Bicep file exists
if [ ! -f "$BICEP_FILE" ]; then
    echo -e "${RED}❌ Bicep file not found: $BICEP_FILE${NC}"
    exit 1
fi

# Validate the Bicep template first
echo -e "${YELLOW}Validating Bicep template...${NC}"
az deployment sub validate \
    --location "$LOCATION" \
    --template-file "$BICEP_FILE" \
    --parameters \
        resourceGroupName="$RESOURCE_GROUP_NAME" \
        location="$LOCATION" \
        storageAccountName="${AZURE_STORAGE_ACCOUNT_NAME}" \
        keyVaultName="${AZURE_KEY_VAULT_NAME}" \
        amlWorkspaceName="${AZURE_ML_WORKSPACE_NAME}" \
        computeName="${AZURE_COMPUTE_NAME}"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Template validation failed. Please check the template.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Template validation passed.${NC}"

# Deploy the complete Bicep template
echo -e "${YELLOW}Starting complete deployment...${NC}"
az deployment sub create \
    --name "$DEPLOYMENT_NAME" \
    --location "$LOCATION" \
    --template-file "$BICEP_FILE" \
    --parameters \
        resourceGroupName="$RESOURCE_GROUP_NAME" \
        location="$LOCATION" \
        storageAccountName="${AZURE_STORAGE_ACCOUNT_NAME}" \
        keyVaultName="${AZURE_KEY_VAULT_NAME}" \
        amlWorkspaceName="${AZURE_ML_WORKSPACE_NAME}" \
        computeName="${AZURE_COMPUTE_NAME}" \
    --verbose

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Complete deployment finished successfully!${NC}"
    
    # Get deployment outputs
    echo -e "${GREEN}Deployment Outputs:${NC}"
    az deployment sub show \
        --name "$DEPLOYMENT_NAME" \
        --query properties.outputs \
        --output table
        
    echo ""
    echo -e "${GREEN}🎉 Azure ML Infrastructure Deployment Complete!${NC}"
    echo ""
    echo -e "${BLUE}📋 What was deployed:${NC}"
    echo "✅ Resource Group: $RESOURCE_GROUP_NAME"
    echo "✅ Storage Account with security best practices"
    echo "✅ Key Vault with RBAC authorization enabled"
    echo "✅ Log Analytics Workspace for monitoring"
    echo "✅ Application Insights for ML monitoring"
    echo "✅ Azure ML Workspace with system-assigned managed identity"
    echo "✅ Compute Cluster with system-assigned managed identity (auto-scales 0-2 nodes)"
    echo ""
    echo -e "${GREEN}🔐 Managed Identity Configuration:${NC}"
    echo "✅ ML Workspace has system-assigned managed identity with:"
    echo "   • Storage Blob Data Contributor role (read/write blob data)"
    echo "   • Storage Account Contributor role (manage containers)"
    echo "   • Key Vault Secrets User role (access secrets)"
    echo "✅ Compute Cluster has system-assigned managed identity with:"
    echo "   • Storage Blob Data Contributor role (read/write blob data)"
    echo "   • Storage Table Data Contributor role (read/write table data)"
    echo "   • Storage Account Contributor role (manage containers and tables)"
    echo "   • Key Vault Secrets User role (access secrets)"
    echo ""
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo "1. Navigate to Azure ML Studio: https://ml.azure.com"
    echo "2. Select your workspace in the resource group: $RESOURCE_GROUP_NAME"
    echo "3. Upload your training data to the default datastore"
    echo "4. Create and run your sentiment analysis pipeline"
    echo ""
    echo -e "${YELLOW}✨ All managed identity authentication issues should now be resolved!${NC}"
    echo -e "${YELLOW}Your ML pipelines should run without permission errors.${NC}"
    
else
    echo -e "${RED}❌ Complete deployment failed. Please check the error messages above.${NC}"
    exit 1
fi
