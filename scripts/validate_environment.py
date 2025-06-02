#!/usr/bin/env python3
"""
Environment Configuration Validation Script

This script validates the environment configuration for the Azure ML sentiment analysis project.
It checks for required variables, validates formats, and provides helpful error messages.

Usage:
    python scripts/validate_environment.py
    python scripts/validate_environment.py --env-file .env.prod
    python scripts/validate_environment.py --verbose
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ python-dotenv not installed. Install with: pip install python-dotenv")
    sys.exit(1)


class EnvironmentValidator:
    """Validates environment configuration for Azure ML project."""
    
    def __init__(self, env_file: str = None, verbose: bool = False):
        """
        Initialize the validator.
        
        Args:
            env_file: Path to environment file (defaults to .env.local then .env)
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.env_file = env_file
        self.errors = []
        self.warnings = []
        self.info = []
        
        # Load environment variables
        self._load_environment()
    
    def _load_environment(self) -> None:
        """Load environment variables from file."""
        if self.env_file:
            if not os.path.exists(self.env_file):
                self.errors.append(f"Environment file not found: {self.env_file}")
                return
            load_dotenv(self.env_file)
            self.info.append(f"Loaded environment from: {self.env_file}")
        else:
            # Try .env.local first, then .env
            if os.path.exists('.env.local'):
                load_dotenv('.env.local')
                self.info.append("Loaded environment from: .env.local")
            elif os.path.exists('.env'):
                load_dotenv('.env')
                self.info.append("Loaded environment from: .env")
            else:
                self.errors.append("No environment file found (.env.local or .env)")
    
    def validate_required_variables(self) -> bool:
        """Validate that all required environment variables are set."""
        required_vars = {
            'AZURE_SUBSCRIPTION_ID': 'Azure subscription ID',
            'AZURE_RESOURCE_GROUP_NAME': 'Azure resource group name',
            'AZURE_LOCATION': 'Azure region/location',
            'AZURE_STORAGE_ACCOUNT_NAME': 'Azure storage account name',
            'AZURE_KEY_VAULT_NAME': 'Azure Key Vault name',
            'AZURE_ML_WORKSPACE_NAME': 'Azure ML workspace name',
            'AZURE_COMPUTE_NAME': 'Azure ML compute cluster name'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value or value.strip() == "":
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            self.errors.append("Missing required environment variables:")
            for var in missing_vars:
                self.errors.append(f"  - {var}")
            return False
        
        self.info.append("✅ All required environment variables are set")
        return True
    
    def validate_azure_subscription_id(self) -> bool:
        """Validate Azure subscription ID format."""
        subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
        if not subscription_id:
            return True  # Already handled in required variables check
        
        # Azure subscription ID should be a GUID
        guid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(guid_pattern, subscription_id, re.IGNORECASE):
            self.errors.append(f"Invalid Azure subscription ID format: {subscription_id}")
            self.errors.append("  Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
            return False
        
        self.info.append("✅ Azure subscription ID format is valid")
        return True
    
    def validate_azure_location(self) -> bool:
        """Validate Azure location."""
        location = os.getenv('AZURE_LOCATION')
        if not location:
            return True  # Already handled in required variables check
        
        # Common Azure locations
        valid_locations = [
            'uksouth', 'ukwest', 'eastus', 'eastus2', 'westus', 'westus2', 'westus3',
            'centralus', 'northcentralus', 'southcentralus', 'westcentralus',
            'canadacentral', 'canadaeast', 'brazilsouth', 'northeurope', 'westeurope',
            'francecentral', 'francesouth', 'germanywestcentral', 'norwayeast',
            'switzerlandnorth', 'swedencentral', 'australiaeast', 'australiasoutheast',
            'eastasia', 'southeastasia', 'japaneast', 'japanwest', 'koreacentral',
            'koreasouth', 'southindia', 'centralindia', 'westindia', 'southafricanorth'
        ]
        
        if location.lower() not in valid_locations:
            self.warnings.append(f"Unusual Azure location: {location}")
            self.warnings.append("  Please verify this is a valid Azure region")
        else:
            self.info.append(f"✅ Azure location is valid: {location}")
        
        return True
    
    def validate_resource_names(self) -> bool:
        """Validate Azure resource naming conventions."""
        resources = {
            'AZURE_STORAGE_ACCOUNT_NAME': {
                'min_length': 3,
                'max_length': 24,
                'pattern': r'^[a-z0-9]+$',
                'description': 'Storage account names must be 3-24 characters, lowercase letters and numbers only'
            },
            'AZURE_KEY_VAULT_NAME': {
                'min_length': 3,
                'max_length': 24,
                'pattern': r'^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$',
                'description': 'Key Vault names must be 3-24 characters, start with letter, alphanumeric and hyphens only'
            },
            'AZURE_ML_WORKSPACE_NAME': {
                'min_length': 3,
                'max_length': 33,
                'pattern': r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$',
                'description': 'ML workspace names must be 3-33 characters, alphanumeric and hyphens only'
            },
            'AZURE_COMPUTE_NAME': {
                'min_length': 2,
                'max_length': 24,
                'pattern': r'^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$',
                'description': 'Compute names must be 2-16 characters, start with letter, alphanumeric and hyphens only'
            }
        }
        
        all_valid = True
        for var_name, rules in resources.items():
            value = os.getenv(var_name)
            if not value:
                continue  # Already handled in required variables check
            
            # Check length
            if len(value) < rules['min_length'] or len(value) > rules['max_length']:
                self.errors.append(f"Invalid {var_name} length: {len(value)} characters")
                self.errors.append(f"  Must be {rules['min_length']}-{rules['max_length']} characters")
                all_valid = False
                continue
            
            # Check pattern
            if not re.match(rules['pattern'], value):
                self.errors.append(f"Invalid {var_name} format: {value}")
                self.errors.append(f"  {rules['description']}")
                all_valid = False
                continue
            
            self.info.append(f"✅ {var_name} format is valid: {value}")
        
        return all_valid
    
    def validate_numeric_values(self) -> bool:
        """Validate numeric configuration values."""
        numeric_vars = {
            'ML_BATCH_SIZE': {'min': 1, 'max': 1000, 'default': '16'},
            'COMPUTE_MIN_NODE_COUNT': {'min': 0, 'max': 100, 'default': '0'},
            'COMPUTE_MAX_NODE_COUNT': {'min': 1, 'max': 1000, 'default': '2'},
            'LOG_ANALYTICS_RETENTION_DAYS': {'min': 7, 'max': 730, 'default': '30'},
            'KEY_VAULT_SOFT_DELETE_RETENTION_DAYS': {'min': 7, 'max': 90, 'default': '7'},
            'PIPELINE_POLL_INTERVAL': {'min': 10, 'max': 3600, 'default': '30'},
            'MONTHLY_BUDGET_LIMIT': {'min': 1, 'max': 100000, 'default': '100'}
        }
        
        all_valid = True
        for var_name, rules in numeric_vars.items():
            value = os.getenv(var_name, rules['default'])
            
            try:
                numeric_value = int(value)
                if numeric_value < rules['min'] or numeric_value > rules['max']:
                    self.warnings.append(f"{var_name} value {numeric_value} is outside recommended range")
                    self.warnings.append(f"  Recommended range: {rules['min']}-{rules['max']}")
                else:
                    if self.verbose:
                        self.info.append(f"✅ {var_name} is valid: {numeric_value}")
            except ValueError:
                self.errors.append(f"Invalid numeric value for {var_name}: {value}")
                all_valid = False
        
        return all_valid
    
    def validate_boolean_values(self) -> bool:
        """Validate boolean configuration values."""
        boolean_vars = [
            'STORAGE_HTTPS_TRAFFIC_ONLY', 'STORAGE_ALLOW_BLOB_PUBLIC_ACCESS',
            'KEY_VAULT_ENABLE_RBAC_AUTHORIZATION', 'ML_WORKSPACE_HBI_WORKSPACE',
            'ML_WORKSPACE_V1_LEGACY_MODE', 'COMPUTE_ENABLE_NODE_PUBLIC_IP',
            'COMPUTE_ISOLATED_NETWORK', 'USE_MANAGED_IDENTITY', 'DEBUG_MODE',
            'DEV_MODE', 'ENABLE_DETAILED_LOGGING'
        ]
        
        valid_boolean_values = ['true', 'false', 'True', 'False', 'TRUE', 'FALSE', '1', '0']
        all_valid = True
        
        for var_name in boolean_vars:
            value = os.getenv(var_name)
            if value and value not in valid_boolean_values:
                self.warnings.append(f"Unusual boolean value for {var_name}: {value}")
                self.warnings.append(f"  Expected: true/false, True/False, or 1/0")
            elif value and self.verbose:
                self.info.append(f"✅ {var_name} is valid: {value}")
        
        return all_valid

    
    def check_file_permissions(self) -> bool:
        """Check file permissions for environment files."""
        env_files = ['.env', '.env.local', '.env.dev', '.env.test', '.env.prod']
        
        for env_file in env_files:
            if os.path.exists(env_file):
                file_stat = os.stat(env_file)
                file_mode = oct(file_stat.st_mode)[-3:]
                
                # Check if file is readable by others (security concern)
                if file_mode[2] in ['4', '5', '6', '7']:  # Others have read permission
                    self.warnings.append(f"Environment file {env_file} is readable by others")
                    self.warnings.append(f"  Consider: chmod 600 {env_file}")
                elif self.verbose:
                    self.info.append(f"✅ {env_file} has appropriate permissions")
        
        return True
    
    def check_gitignore(self) -> bool:
        """Check if sensitive environment files are in .gitignore."""
        gitignore_path = '.gitignore'
        if not os.path.exists(gitignore_path):
            self.warnings.append(".gitignore file not found")
            return True
        
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
        
        sensitive_files = ['.env.local', '.env.dev', '.env.test', '.env.prod']
        missing_from_gitignore = []
        
        for sensitive_file in sensitive_files:
            if sensitive_file not in gitignore_content:
                missing_from_gitignore.append(sensitive_file)
        
        if missing_from_gitignore:
            self.warnings.append("Sensitive environment files not in .gitignore:")
            for file in missing_from_gitignore:
                self.warnings.append(f"  - {file}")
            self.warnings.append("Consider adding these to prevent accidental commits")
        else:
            self.info.append("✅ Sensitive environment files are in .gitignore")
        
        return True
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        if self.errors:  # If we couldn't load environment, skip other checks
            return False
        
        checks = [
            self.validate_required_variables,
            self.validate_azure_subscription_id,
            self.validate_azure_location,
            self.validate_resource_names,
            self.validate_numeric_values,
            self.validate_boolean_values,
            self.check_file_permissions,
            self.check_gitignore
        ]
        
        all_passed = True
        for check in checks:
            try:
                if not check():
                    all_passed = False
            except Exception as e:
                self.errors.append(f"Validation check failed: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def print_results(self) -> None:
        """Print validation results."""
        print("=" * 60)
        print("AZURE ML ENVIRONMENT VALIDATION RESULTS")
        print("=" * 60)
        
        # Print info messages
        if self.info:
            print("\n📋 INFORMATION:")
            for msg in self.info:
                print(f"  {msg}")
        
        # Print warnings
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for msg in self.warnings:
                print(f"  {msg}")
        
        # Print errors
        if self.errors:
            print("\n❌ ERRORS:")
            for msg in self.errors:
                print(f"  {msg}")
        
        # Summary
        print("\n" + "=" * 60)
        if self.errors:
            print("❌ VALIDATION FAILED")
            print("Please fix the errors above before proceeding.")
        elif self.warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS")
            print("Consider addressing the warnings above.")
        else:
            print("✅ VALIDATION PASSED")
            print("Environment configuration looks good!")
        print("=" * 60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Validate Azure ML environment configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_environment.py
  python scripts/validate_environment.py --env-file .env.prod
  python scripts/validate_environment.py --verbose
        """
    )
    
    parser.add_argument(
        '--env-file',
        help='Path to environment file (default: .env.local or .env)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Create validator and run checks
    validator = EnvironmentValidator(
        env_file=args.env_file,
        verbose=args.verbose
    )
    
    success = validator.validate_all()
    validator.print_results()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
