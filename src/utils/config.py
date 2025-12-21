"""
Configuration management utilities
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Load and manage configuration"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            # Try to load example config
            example_path = Path("config.example.yaml")
            if example_path.exists():
                print(f"Warning: {self.config_path} not found. Using example config.")
                print("Please copy config.example.yaml to config.yaml and add your API keys.")
                with open(example_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key_path: Dot-separated path to config value (e.g., 'api_keys.newsapi')
            default: Default value if key not found

        Returns:
            Configuration value

        Example:
            >>> config = Config()
            >>> api_key = config.get('api_keys.newsapi')
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_api_key(self, service: str) -> str:
        """
        Get API key for a service

        Args:
            service: Service name (e.g., 'newsapi')

        Returns:
            API key
        """
        key = self.get(f'api_keys.{service}')
        if not key or key.startswith('YOUR_'):
            raise ValueError(
                f"Please set your {service} API key in config.yaml. "
                f"Copy config.example.yaml to config.yaml and add your keys."
            )
        return key

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access"""
        return self.config[key]

    def __repr__(self) -> str:
        return f"Config(config_path='{self.config_path}')"


# Singleton instance
_config_instance = None


def get_config() -> Config:
    """Get configuration singleton instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
