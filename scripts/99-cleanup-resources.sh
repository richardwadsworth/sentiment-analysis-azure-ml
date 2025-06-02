#!/bin/bash

# Azure ML Sentiment Analysis - Cleanup Existing Resources
# This script removes existing resources to allow for a clean deployment

set -e

# Load environment variables
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
elif [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Configuration from environment variables
RESOURCE_GROUP_NAME="${AZURE_RESOURCE_GROUP_NAME:-sentiment-analysis-rg}"

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Azure ML Sentiment Analysis - Cleanup Existing Resources${NC}"
echo "======================================================="

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

# Check if resource group exists
echo -e "${YELLOW}Checking if resource group exists...${NC}"
if ! az group show --name "$RESOURCE_GROUP_NAME" &> /dev/null; then
    echo -e "${GREEN}Resource group '$RESOURCE_GROUP_NAME' does not exist. Nothing to clean up.${NC}"
    exit 0
fi

echo -e "${BLUE}Found resource group: $RESOURCE_GROUP_NAME${NC}"
echo -e "${YELLOW}This will delete ALL resources in the resource group.${NC}"
echo -e "${RED}WARNING: This action cannot be undone!${NC}"
echo ""

# List resources that will be deleted
echo -e "${BLUE}Resources that will be deleted:${NC}"
az resource list --resource-group "$RESOURCE_GROUP_NAME" --output table

echo ""
read -p "Are you sure you want to delete the entire resource group and all its resources? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Cleanup cancelled.${NC}"
    exit 0
fi

echo -e "${YELLOW}Deleting resource group and all resources...${NC}"
az group delete --name "$RESOURCE_GROUP_NAME" --yes --no-wait

echo -e "${GREEN}✅ Cleanup initiated. Resource group deletion is running in the background.${NC}"
echo -e "${BLUE}You can now run ./deploy-complete.sh to deploy fresh resources.${NC}"
echo ""
echo -e "${YELLOW}Note: It may take several minutes for the deletion to complete.${NC}"
echo -e "${YELLOW}You can check the status in the Azure Portal.${NC}"
