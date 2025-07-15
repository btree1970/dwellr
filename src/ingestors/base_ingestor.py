from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SyncResult:
    source: str
    total_processed: int
    new_listings: int
    duplicates_skipped: int
    errors: int
    pages_processed: int
    success: bool
    error_message: Optional[str] = None


class BaseIngestor(ABC):
    """Abstract base class for all listing ingestors"""

    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> "BaseIngestor":
        """
        Create ingestor instance from complete configuration dictionary

        Args:
            config: Complete configuration dictionary containing:
                - credentials: Resolved credential values (not env var names)
                - All ingestor parameters (city, max_pages, delays, etc.)
                - Any other ingestor-specific configuration

        Returns:
            Fully configured ingestor instance ready to sync

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        pass

    @abstractmethod
    def sync(self) -> SyncResult:
        """
        Execute syncing using the configuration provided at creation time

        Returns:
            SyncResult with standardized statistics

        Raises:
            Exception: For ingestor-specific errors
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get the unique identifier for this ingestor source

        Returns:
            String identifier (e.g., 'listing_project', 'streeteasy')
        """
        pass
