"""Central manager for all crawler sources"""

import logging
import os
from typing import Any, Dict, List, Optional, Type

import yaml

from src.crawlers.base_crawler import BaseCrawler, CrawlResult
from src.crawlers.listing_project import ListingProject

logger = logging.getLogger(__name__)


class CrawlerManager:
    """Central registry and factory for crawler sources"""

    def __init__(self, config_file: str = "crawlers.yaml"):
        self._crawlers: Dict[str, Type[BaseCrawler]] = {}
        self._config_file = config_file
        self._crawler_configs: Dict[str, Dict[str, Any]] = {}
        self._load_crawler_configs()
        self._register_crawlers()

    def _load_crawler_configs(self):
        """Load crawler configurations from YAML file"""
        try:
            # Look for config file in project root
            config_path = self._config_file
            if not os.path.exists(config_path):
                # Try relative to this module
                config_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", self._config_file
                )

            if not os.path.exists(config_path):
                logger.warning(f"Crawler config file not found: {self._config_file}")
                self._crawler_configs = {}
                return

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not config_data or "crawlers" not in config_data:
                logger.warning(
                    f"Invalid crawler config file format: {self._config_file}"
                )
                self._crawler_configs = {}
                return

            self._crawler_configs = config_data["crawlers"]
            logger.info(f"Loaded configs for {len(self._crawler_configs)} crawlers")

        except Exception as e:
            logger.error(f"Error loading crawler configs: {e}")
            self._crawler_configs = {}

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

    def get_crawler_config(self, source_name: str) -> Dict[str, Any]:
        """
        Get resolved configuration for a specific crawler source

        Args:
            source_name: Name of the crawler source

        Returns:
            Configuration dictionary with resolved credentials

        Raises:
            ValueError: If source_name is not configured
        """
        if source_name not in self._crawler_configs:
            available = list(self._crawler_configs.keys())
            raise ValueError(
                f"No configuration found for '{source_name}'. Available: {available}"
            )

        source_config = self._crawler_configs[source_name].copy()

        # Resolve credentials from environment variables
        if "credentials" in source_config:
            resolved_creds = self._resolve_credentials(source_config["credentials"])
            source_config["credentials"] = resolved_creds

        return source_config

    def _merge_crawler_config(
        self, base_config: Dict[str, Any], crawl_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge runtime crawl parameters with base YAML configuration

        Args:
            base_config: Base config from YAML (credentials + defaults)
            crawl_params: Runtime parameters to override/add

        Returns:
            Complete merged configuration
        """
        # Start with base config
        merged = base_config.copy()

        # Merge defaults with runtime params (runtime params take precedence)
        if "defaults" in merged:
            defaults = merged["defaults"].copy()
            defaults.update(crawl_params)
            merged.update(defaults)
            # Remove the defaults section since we've merged it
            del merged["defaults"]
        else:
            # No defaults section, just add runtime params
            merged.update(crawl_params)

        return merged

    def _register_crawlers(self):
        """Register all available crawler classes"""
        try:
            self.register_crawler("listing_project", ListingProject)
        except ImportError as e:
            logger.warning(f"Failed to register ListingProject crawler: {e}")

    def register_crawler(self, source_name: str, crawler_class: Type[BaseCrawler]):
        """
        Register a new crawler class

        Args:
            source_name: Unique identifier for the crawler
            crawler_class: Class that implements BaseCrawler
        """
        self._crawlers[source_name] = crawler_class
        logger.info(f"Registered crawler: {source_name}")

    def get_crawler(
        self, source_name: str, crawl_params: Optional[Dict[str, Any]] = None
    ) -> BaseCrawler:
        """
        Get a fully configured crawler instance for the specified source

        Args:
            source_name: Name of the crawler source
            crawl_params: Runtime crawling parameters to merge with YAML defaults

        Returns:
            Fully configured crawler instance ready to crawl

        Raises:
            ValueError: If source_name is not registered
        """
        if source_name not in self._crawlers:
            available = list(self._crawlers.keys())
            raise ValueError(
                f"Unknown crawler source '{source_name}'. Available: {available}"
            )

        # Create new instance each time to avoid state issues
        crawler_class = self._crawlers[source_name]

        try:
            # Get base configuration for this crawler (credentials + defaults)
            base_config = self.get_crawler_config(source_name)

            # Merge runtime parameters with YAML defaults
            complete_config = self._merge_crawler_config(
                base_config, crawl_params or {}
            )

            # Create instance using from_config method (validation happens here)
            instance = crawler_class.from_config(complete_config)
            logger.info(f"Created {source_name} crawler instance")
            return instance
        except Exception as e:
            logger.error(f"Failed to create {source_name} crawler: {e}")
            raise

    def get_available_sources(self) -> List[str]:
        """
        Get list of all registered crawler sources

        Returns:
            List of source names
        """
        return list(self._crawlers.keys())

    def get_enabled_sources(self) -> List[str]:
        """
        Get list of enabled crawler sources from configuration

        Returns:
            List of enabled source names (all registered sources by default)
        """
        # For now, return all available sources
        # Could be extended to support enabled/disabled flags in YAML
        return list(self._crawler_configs.keys())

    def get_source_default_config(self, source_name: str) -> Dict[str, Any]:
        """
        Get default configuration for a specific source

        Args:
            source_name: Name of the crawler source

        Returns:
            Default configuration dictionary from YAML
        """
        config = self.get_crawler_config(source_name)
        return config.get("defaults", {})

    def crawl_source(
        self, source_name: str, crawl_params: Optional[Dict[str, Any]] = None
    ) -> CrawlResult:
        """
        Execute crawling for a specific source

        Args:
            source_name: Name of the crawler source
            crawl_params: Runtime crawling parameters

        Returns:
            CrawlResult with statistics
        """
        crawler = self.get_crawler(source_name, crawl_params)

        logger.info(f"Starting crawl for {source_name}")
        try:
            result = crawler.crawl()
            logger.info(f"Crawl completed for {source_name}: {result}")
            return result
        except Exception as e:
            logger.error(f"Crawl failed for {source_name}: {e}")
            raise

    def crawl_all_enabled(
        self, crawl_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, CrawlResult]:
        """
        Execute crawling for all enabled sources

        Args:
            crawl_params: Base crawling parameters to use for all sources

        Returns:
            Dictionary mapping source names to their CrawlResults
        """
        results: Dict[str, CrawlResult] = {}
        enabled_sources = self.get_enabled_sources()

        for source_name in enabled_sources:
            try:
                result = self.crawl_source(source_name, crawl_params)
                results[source_name] = result
            except Exception as e:
                logger.error(f"Failed to crawl {source_name}: {e}")
                results[source_name] = CrawlResult(
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


crawler_manager = CrawlerManager()
