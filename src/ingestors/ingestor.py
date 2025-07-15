"""Central manager for all ingestor sources"""

import logging
import os
from typing import Any, Dict, List, Optional, Type

import yaml

from src.ingestors.base_ingestor import BaseIngestor, SyncResult
from src.ingestors.listing_project import ListingProjectIngestor

logger = logging.getLogger(__name__)


class Ingestor:

    def __init__(self, config_file: str = "ingestors.yaml"):
        self._ingestors: Dict[str, Type[BaseIngestor]] = {}
        self._config_file = config_file
        self._ingestor_configs: Dict[str, Dict[str, Any]] = {}
        self._load_ingestor_configs()
        self._register_ingestors()

    def _load_ingestor_configs(self):
        try:
            # Look for config file in project root
            config_path = self._config_file
            if not os.path.exists(config_path):
                # Try relative to this module
                config_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", self._config_file
                )

            if not os.path.exists(config_path):
                logger.warning(f"Ingestor config file not found: {self._config_file}")
                self._ingestor_configs = {}
                return

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not config_data or "ingestors" not in config_data:
                logger.warning(
                    f"Invalid ingestor config file format: {self._config_file}"
                )
                self._ingestor_configs = {}
                return

            self._ingestor_configs = config_data["ingestors"]
            logger.info(f"Loaded configs for {len(self._ingestor_configs)} ingestors")

        except Exception as e:
            logger.error(f"Error loading ingestor configs: {e}")
            self._ingestor_configs = {}

    def _resolve_credentials(
        self, credentials_config: Dict[str, str]
    ) -> Dict[str, Any]:
        """Resolve credential environment variables to actual values"""
        resolved: Dict[str, Any] = {}

        for cred_key, env_var_name in credentials_config.items():
            if cred_key.endswith("_env_var"):
                # Remove _env_var suffix to get actual credential name
                actual_key = cred_key[:-8]  # Remove "_env_var"
                env_value = os.getenv(env_var_name)
                if env_value:
                    resolved[actual_key] = env_value
                else:
                    logger.warning(
                        f"Environment variable {env_var_name} not set for {actual_key}"
                    )

        return resolved

    def get_ingestor_config(self, source_name: str) -> Dict[str, Any]:
        """
        Get resolved configuration for a specific ingestor source

        Args:
            source_name: Name of the ingestor source

        Returns:
            Configuration dictionary with resolved credentials

        Raises:
            ValueError: If source_name is not configured
        """
        if source_name not in self._ingestor_configs:
            available = list(self._ingestor_configs.keys())
            raise ValueError(
                f"No configuration found for '{source_name}'. Available: {available}"
            )

        source_config = self._ingestor_configs[source_name].copy()

        # Resolve credentials from environment variables
        if "credentials" in source_config:
            resolved_creds = self._resolve_credentials(source_config["credentials"])
            source_config["credentials"] = resolved_creds

        return source_config

    def _merge_ingestor_config(
        self, base_config: Dict[str, Any], sync_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge runtime sync parameters with base YAML configuration

        Args:
            base_config: Base config from YAML (credentials + defaults)
            sync_params: Runtime parameters to override/add

        Returns:
            Complete merged configuration
        """
        # Start with base config
        merged = base_config.copy()

        # Merge defaults with runtime params (runtime params take precedence)
        if "defaults" in merged:
            defaults = merged["defaults"].copy()
            defaults.update(sync_params)
            merged.update(defaults)
            # Remove the defaults section since we've merged it
            del merged["defaults"]
        else:
            # No defaults section, just add runtime params
            merged.update(sync_params)

        return merged

    def _register_ingestors(self):
        """Register all available ingestor classes"""
        try:
            self.register_ingestor("listing_project", ListingProjectIngestor)
        except ImportError as e:
            logger.warning(f"Failed to register ListingProjectIngestor: {e}")

    def register_ingestor(self, source_name: str, ingestor_class: Type[BaseIngestor]):
        """
        Register a new ingestor class

        Args:
            source_name: Unique identifier for the ingestor
            ingestor_class: Class that implements BaseIngestor
        """
        self._ingestors[source_name] = ingestor_class
        logger.info(f"Registered ingestor: {source_name}")

    def get_ingestor(
        self, source_name: str, sync_params: Optional[Dict[str, Any]] = None
    ) -> BaseIngestor:
        """
        Get a fully configured ingestor instance for the specified source

        Args:
            source_name: Name of the ingestor source
            sync_params: Runtime sync parameters to merge with YAML defaults

        Returns:
            Fully configured ingestor instance ready to sync

        Raises:
            ValueError: If source_name is not registered
        """
        if source_name not in self._ingestors:
            available = list(self._ingestors.keys())
            raise ValueError(
                f"Unknown ingestor source '{source_name}'. Available: {available}"
            )

        # Create new instance each time to avoid state issues
        ingestor_class = self._ingestors[source_name]

        try:
            # Get base configuration for this ingestor (credentials + defaults)
            base_config = self.get_ingestor_config(source_name)

            # Merge runtime parameters with YAML defaults
            complete_config = self._merge_ingestor_config(
                base_config, sync_params or {}
            )

            # Create instance using from_config method (validation happens here)
            instance = ingestor_class.from_config(complete_config)
            logger.info(f"Created {source_name} ingestor instance")
            return instance
        except Exception as e:
            logger.error(f"Failed to create {source_name} ingestor: {e}")
            raise

    def get_available_sources(self) -> List[str]:
        """
        Get list of all registered ingestor sources

        Returns:
            List of source names
        """
        return list(self._ingestors.keys())

    def get_enabled_sources(self) -> List[str]:
        """
        Get list of enabled ingestor sources from configuration

        Returns:
            List of enabled source names (all registered sources by default)
        """
        # For now, return all available sources
        # Could be extended to support enabled/disabled flags in YAML
        return list(self._ingestor_configs.keys())

    def get_source_default_config(self, source_name: str) -> Dict[str, Any]:
        """
        Get default configuration for a specific source

        Args:
            source_name: Name of the ingestor source

        Returns:
            Default configuration dictionary from YAML
        """
        config = self.get_ingestor_config(source_name)
        return config.get("defaults", {})

    def sync_source(
        self, source_name: str, sync_params: Optional[Dict[str, Any]] = None
    ) -> SyncResult:
        """
        Execute syncing for a specific source

        Args:
            source_name: Name of the ingestor source
            sync_params: Runtime sync parameters

        Returns:
            SyncResult with statistics
        """
        ingestor = self.get_ingestor(source_name, sync_params)

        logger.info(f"Starting sync for {source_name}")
        try:
            result = ingestor.sync()
            logger.info(f"Sync completed for {source_name}: {result}")
            return result
        except Exception as e:
            logger.error(f"Sync failed for {source_name}: {e}")
            raise

    def sync_all_enabled(
        self, sync_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, SyncResult]:
        """
        Execute syncing for all enabled sources

        Args:
            sync_params: Base sync parameters to use for all sources

        Returns:
            Dictionary mapping source names to their SyncResults
        """
        results: Dict[str, SyncResult] = {}
        enabled_sources = self.get_enabled_sources()

        for source_name in enabled_sources:
            try:
                result = self.sync_source(source_name, sync_params)
                results[source_name] = result
            except Exception as e:
                logger.error(f"Failed to sync {source_name}: {e}")
                results[source_name] = SyncResult(
                    source=source_name,
                    total_processed=0,
                    new_listings=0,
                    duplicates_skipped=0,
                    errors=1,
                    pages_processed=0,
                    success=False,
                    error_message=str(e),
                )
        return results


ingestor = Ingestor()
