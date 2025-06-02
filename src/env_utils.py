#!/usr/bin/env python3
"""
Environment Variable Utilities

This module provides utilities for loading and processing environment variables
with support for placeholder replacement to ensure globally unique resource names.

Author: AI Assistant
Date: 2025-01-06
"""

import os
import re
import hashlib
import time
from typing import Dict, Optional, Any
from dotenv import load_dotenv


class EnvironmentManager:
    """
    Manages environment variable loading with placeholder replacement.
    
    Supports placeholders like {random}, {timestamp}, {hash} for generating
    globally unique resource names at runtime.
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize the environment manager.
        
        Args:
            env_file: Path to specific environment file, or None to use default loading
        """
        self.env_file = env_file
        self._random_suffix = None
        self._timestamp_suffix = None
        self._load_environment()
    
    def _load_environment(self) -> None:
        """Load environment variables from files."""
        if self.env_file:
            load_dotenv(self.env_file)
        else:
            # Try .env.local first, then .env (don't override .env.local values)
            load_dotenv('.env')  # Load defaults first
            load_dotenv('.env.local', override=True)  # Override with local values
    
    def _get_random_suffix(self, length: int = 5) -> str:
        """
        Generate a consistent random suffix for the session.
        
        Args:
            length: Length of the random suffix (default: 5)
        
        Returns:
            str: Random suffix of specified length
        """
        if self._random_suffix is None:
            # Generate based on current time and process ID for uniqueness
            seed = f"{time.time()}{os.getpid()}"
            hash_obj = hashlib.md5(seed.encode())
            self._random_suffix = hash_obj.hexdigest()
        
        return self._random_suffix[:length]
    
    def _get_timestamp_suffix(self) -> str:
        """
        Generate a timestamp-based suffix.
        
        Returns:
            str: Timestamp suffix in format YYYYMMDDHHMMSS
        """
        if self._timestamp_suffix is None:
            self._timestamp_suffix = time.strftime("%Y%m%d%H%M%S")
        
        return self._timestamp_suffix
    
    def _get_hash_suffix(self, input_string: str) -> str:
        """
        Generate a hash-based suffix from input string.
        
        Args:
            input_string: String to hash
            
        Returns:
            str: 8-character hash suffix
        """
        hash_obj = hashlib.sha256(input_string.encode())
        return hash_obj.hexdigest()[:8]
    
    def _replace_placeholders(self, value: str) -> str:
        """
        Replace placeholders in environment variable values.
        
        Supported placeholders:
        - {random}: 5-character random suffix (consistent per session)
        - {random8}: 8-character random suffix (consistent per session)
        - {timestamp}: Timestamp in YYYYMMDDHHMMSS format
        - {hash:input}: 8-character hash of 'input'
        
        Args:
            value: Environment variable value with placeholders
            
        Returns:
            str: Value with placeholders replaced
        """
        if not isinstance(value, str):
            return value
        
        # Replace {random8} placeholder (8-character version)
        if '{random8}' in value:
            value = value.replace('{random8}', self._get_random_suffix(8))
        
        # Replace {random} placeholder (5-character version for backward compatibility)
        if '{random}' in value:
            value = value.replace('{random}', self._get_random_suffix(5))
        
        # Replace {timestamp} placeholder
        if '{timestamp}' in value:
            value = value.replace('{timestamp}', self._get_timestamp_suffix())
        
        # Replace {hash:input} placeholders
        hash_pattern = r'\{hash:([^}]+)\}'
        hash_matches = re.findall(hash_pattern, value)
        for hash_input in hash_matches:
            hash_suffix = self._get_hash_suffix(hash_input)
            value = value.replace(f'{{hash:{hash_input}}}', hash_suffix)
        
        return value
    
    def get_env(self, key: str, default: Any = None, required: bool = False) -> Any:
        """
        Get environment variable with placeholder replacement.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            required: Whether the variable is required
            
        Returns:
            Any: Environment variable value with placeholders replaced
            
        Raises:
            ValueError: If required variable is missing
        """
        value = os.getenv(key, default)
        
        if required and (value is None or value == ""):
            raise ValueError(f"Required environment variable '{key}' is not set")
        
        if value is not None:
            value = self._replace_placeholders(str(value))
        
        return value
    
    def get_env_bool(self, key: str, default: bool = False) -> bool:
        """
        Get boolean environment variable.
        
        Args:
            key: Environment variable name
            default: Default boolean value
            
        Returns:
            bool: Boolean value
        """
        value = self.get_env(key, str(default).lower())
        return str(value).lower() in ('true', '1', 'yes', 'on')
    
    def get_env_int(self, key: str, default: int = 0) -> int:
        """
        Get integer environment variable.
        
        Args:
            key: Environment variable name
            default: Default integer value
            
        Returns:
            int: Integer value
        """
        value = self.get_env(key, str(default))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_env_float(self, key: str, default: float = 0.0) -> float:
        """
        Get float environment variable.
        
        Args:
            key: Environment variable name
            default: Default float value
            
        Returns:
            float: Float value
        """
        value = self.get_env(key, str(default))
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_all_env_vars(self) -> Dict[str, str]:
        """
        Get all environment variables with placeholders replaced.
        
        Returns:
            Dict[str, str]: Dictionary of all environment variables
        """
        env_vars = {}
        for key, value in os.environ.items():
            env_vars[key] = self._replace_placeholders(value)
        
        return env_vars
    
    def validate_azure_resource_names(self) -> Dict[str, bool]:
        """
        Validate Azure resource names after placeholder replacement.
        
        Returns:
            Dict[str, bool]: Validation results for each resource
        """
        validation_results = {}
        
        # Storage account name validation
        storage_name = self.get_env('AZURE_STORAGE_ACCOUNT_NAME')
        if storage_name:
            # Must be 3-24 characters, lowercase letters and numbers only
            storage_valid = (
                3 <= len(storage_name) <= 24 and
                re.match(r'^[a-z0-9]+$', storage_name)
            )
            validation_results['storage_account'] = storage_valid
        
        # Key vault name validation
        keyvault_name = self.get_env('AZURE_KEY_VAULT_NAME')
        if keyvault_name:
            # Must be 3-24 characters, start with letter, alphanumeric and hyphens only
            keyvault_valid = (
                3 <= len(keyvault_name) <= 24 and
                re.match(r'^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$', keyvault_name)
            )
            validation_results['key_vault'] = keyvault_valid
        
        return validation_results
    
    def print_resolved_values(self, keys: list = None) -> None:
        """
        Print resolved environment variable values for debugging.
        
        Args:
            keys: List of specific keys to print, or None for common Azure keys
        """
        if keys is None:
            keys = [
                'AZURE_STORAGE_ACCOUNT_NAME',
                'AZURE_KEY_VAULT_NAME',
                'AZURE_ML_WORKSPACE_NAME',
                'AZURE_RESOURCE_GROUP_NAME',
                'AZURE_LOCATION'
            ]
        
        print("Resolved Environment Variables:")
        print("=" * 40)
        for key in keys:
            value = self.get_env(key, 'NOT_SET')
            print(f"{key}: {value}")
        print("=" * 40)


# Global instance for easy access
env_manager = EnvironmentManager()

# Convenience functions for backward compatibility
def get_env(key: str, default: Any = None, required: bool = False) -> Any:
    """Get environment variable with placeholder replacement."""
    return env_manager.get_env(key, default, required)

def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    return env_manager.get_env_bool(key, default)

def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable."""
    return env_manager.get_env_int(key, default)

def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float environment variable."""
    return env_manager.get_env_float(key, default)


if __name__ == "__main__":
    # Test the environment manager
    print("Testing Environment Manager")
    print("=" * 50)
    
    # Test placeholder replacement
    test_env = EnvironmentManager()
    test_env.print_resolved_values()
    
    # Test validation
    validation_results = test_env.validate_azure_resource_names()
    print("\nValidation Results:")
    for resource, is_valid in validation_results.items():
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{resource}: {status}")
