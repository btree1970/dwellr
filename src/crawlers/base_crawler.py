from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CrawlResult:
    source: str
    total_processed: int
    new_listings: int
    duplicates_skipped: int
    errors: int
    pages_processed: int
    success: bool
    error_message: Optional[str] = None


class BaseCrawler(ABC):
    """Abstract base class for all listing crawlers"""

    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> "BaseCrawler":
        """
        Create crawler instance from complete configuration dictionary

        Args:
            config: Complete configuration dictionary containing:
                - credentials: Resolved credential values (not env var names)
                - All crawling parameters (city, max_pages, delays, etc.)
                - Any other crawler-specific configuration

        Returns:
            Fully configured crawler instance ready to crawl

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        pass

    @abstractmethod
    def crawl(self) -> CrawlResult:
        """
        Execute crawling using the configuration provided at creation time

        Returns:
            CrawlResult with standardized statistics

        Raises:
            Exception: For crawler-specific errors
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get the unique identifier for this crawler source

        Returns:
            String identifier (e.g., 'listing_project', 'streeteasy')
        """
        pass
