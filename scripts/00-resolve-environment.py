#!/usr/bin/env python3
"""
Environment Resolution Script

This script resolves environment variable placeholders and validates the configuration
before running the infrastructure deployment. It should be run before any other scripts.

Usage:
    python scripts/00-resolve-environment.py
    python scripts/00-resolve-environment.py --verbose
    python scripts/00-resolve-environment.py --export-shell
"""

import os
import sys
import argparse
from pathlib import Path

# Import environment utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from env_utils import EnvironmentManager

def main():
    """Main function to resolve and validate environment variables."""
    parser = argparse.ArgumentParser(
        description="Resolve environment variable placeholders and validate configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic resolution and validation
  python scripts/00-resolve-environment.py
  
  # Verbose output showing all resolved values
  python scripts/00-resolve-environment.py --verbose
  
  # Export resolved values for shell scripts
  python scripts/00-resolve-environment.py --export-shell > resolved.env
        """
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output including all resolved values'
    )
    parser.add_argument(
        '--export-shell',
        action='store_true',
        help='Export resolved values in shell format (for sourcing)'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate configuration, do not show resolved values'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize environment manager
        env_manager = EnvironmentManager()
        
        if not args.export_shell:
            print("Azure ML Sentiment Analysis - Environment Resolution")
            print("=" * 60)
        
        # Key environment variables to resolve and validate
        key_vars = [
            'AZURE_SUBSCRIPTION_ID',
            'AZURE_RESOURCE_GROUP_NAME',
            'AZURE_LOCATION',
            'AZURE_STORAGE_ACCOUNT_NAME',
            'AZURE_KEY_VAULT_NAME',
            'AZURE_ML_WORKSPACE_NAME',
            'AZURE_COMPUTE_NAME'
        ]
        
        # Resolve placeholders and collect values
        resolved_values = {}
        for var in key_vars:
            resolved_values[var] = env_manager.get_env(var, 'NOT_SET')
        
        if args.export_shell:
            # Export in shell format
            for var, value in resolved_values.items():
                if value != 'NOT_SET':
                    print(f'export {var}="{value}"')
            return
        
        # Display resolved values
        if not args.validate_only:
            print("\n📋 RESOLVED ENVIRONMENT VARIABLES:")
            print("-" * 40)
            for var, value in resolved_values.items():
                if value == 'NOT_SET':
                    print(f"❌ {var}: NOT SET")
                else:
                    print(f"✅ {var}: {value}")
        
        # Validate Azure resource names
        print("\n🔍 VALIDATION RESULTS:")
        print("-" * 40)
        
        validation_results = env_manager.validate_azure_resource_names()
        all_valid = True
        
        for resource, is_valid in validation_results.items():
            status = "✅ VALID" if is_valid else "❌ INVALID"
            resource_name = resolved_values.get(f'AZURE_{resource.upper()}_NAME', 'NOT_SET')
            print(f"{status} {resource}: {resource_name}")
            if not is_valid:
                all_valid = False
        
        # Check for missing required variables
        missing_vars = [var for var, value in resolved_values.items() if value == 'NOT_SET']
        if missing_vars:
            all_valid = False
            print(f"\n❌ MISSING REQUIRED VARIABLES:")
            for var in missing_vars:
                print(f"   - {var}")
        
        # Show length validation for Azure naming limits
        if args.verbose and not args.validate_only:
            print("\n📏 RESOURCE NAME LENGTH VALIDATION:")
            print("-" * 40)
            
            length_limits = {
                'AZURE_STORAGE_ACCOUNT_NAME': 24,
                'AZURE_KEY_VAULT_NAME': 24,
                'AZURE_ML_WORKSPACE_NAME': 33,
                'AZURE_COMPUTE_NAME': 24
            }
            
            for var, limit in length_limits.items():
                value = resolved_values.get(var, '')
                if value and value != 'NOT_SET':
                    length = len(value)
                    status = "✅" if length <= limit else "❌"
                    print(f"{status} {var}: {length}/{limit} characters")
        
        # Summary
        print("\n" + "=" * 60)
        if all_valid:
            print("✅ ENVIRONMENT VALIDATION PASSED")
            print("All required variables are set and resource names are valid.")
            print("You can now proceed with infrastructure deployment.")
        else:
            print("❌ ENVIRONMENT VALIDATION FAILED")
            print("Please fix the issues above before proceeding.")
            print("\nTo fix issues:")
            print("1. Edit your .env.local file")
            print("2. Ensure all required variables are set")
            print("3. Check that resource names meet Azure naming requirements")
            print("4. Re-run this script to validate")
        
        print("=" * 60)
        
        # Exit with appropriate code
        sys.exit(0 if all_valid else 1)
        
    except Exception as e:
        if not args.export_shell:
            print(f"\n❌ Environment resolution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
