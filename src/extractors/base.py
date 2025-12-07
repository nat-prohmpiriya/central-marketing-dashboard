"""Base extractor class with common functionality."""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generator

import httpx

from src.utils.config import get_rate_limits, get_settings
from src.utils.logging import get_logger


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0

    def wait(self) -> None:
        """Wait if necessary to comply with rate limits."""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.interval:
            sleep_time = self.interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()


class ExtractorError(Exception):
    """Base exception for extractor errors."""

    def __init__(self, message: str, platform: str, details: dict[str, Any] | None = None):
        self.message = message
        self.platform = platform
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(ExtractorError):
    """Raised when authentication fails."""

    pass


class RateLimitError(ExtractorError):
    """Raised when rate limit is exceeded."""

    pass


class APIError(ExtractorError):
    """Raised when API returns an error."""

    pass


class BaseExtractor(ABC):
    """Abstract base class for all data extractors.

    Provides common functionality:
    - Authentication handling
    - Rate limiting
    - Retry logic with exponential backoff
    - Error handling
    - Logging
    """

    # Override in subclasses
    platform_name: str = "base"
    base_url: str = ""

    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(f"extractor.{self.platform_name}")

        # Load rate limits from config
        rate_config = get_rate_limits(self.platform_name)
        self.rate_limiter = RateLimiter(
            requests_per_minute=rate_config.get("requests_per_minute", 60)
        )
        self.max_retries = rate_config.get("max_retries", 3)
        self.retry_after_seconds = rate_config.get("retry_after_seconds", 60)

        # HTTP client
        self._client: httpx.Client | None = None

        # Authentication state
        self._authenticated = False
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=30.0,
                headers=self._get_default_headers(),
            )
        return self._client

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for requests. Override in subclasses."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform API.

        Returns:
            True if authentication successful, False otherwise.

        Raises:
            AuthenticationError: If authentication fails.
        """
        pass

    @abstractmethod
    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract data from the platform.

        Args:
            start_date: Start date for data extraction.
            end_date: End date for data extraction.
            **kwargs: Additional platform-specific parameters.

        Yields:
            Dictionary containing extracted data records.

        Raises:
            ExtractorError: If extraction fails.
        """
        pass

    def _ensure_authenticated(self) -> None:
        """Ensure we have valid authentication."""
        if not self._authenticated or self._is_token_expired():
            self.logger.info("Authenticating with platform", platform=self.platform_name)
            if not self.authenticate():
                raise AuthenticationError(
                    message="Failed to authenticate",
                    platform=self.platform_name,
                )
            self._authenticated = True

    def _is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        if self._token_expires_at is None:
            return False
        return datetime.now() >= self._token_expires_at

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path.
            params: Query parameters.
            json: JSON body for POST/PUT requests.
            **kwargs: Additional arguments for httpx.

        Returns:
            Response data as dictionary.

        Raises:
            RateLimitError: If rate limit exceeded after retries.
            APIError: If API returns an error.
        """
        self._ensure_authenticated()

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                # Apply rate limiting
                self.rate_limiter.wait()

                # Make request
                self.logger.debug(
                    "Making API request",
                    method=method,
                    endpoint=endpoint,
                    attempt=attempt + 1,
                )

                response = self.client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    json=json,
                    **kwargs,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", self.retry_after_seconds)
                    )
                    self.logger.warning(
                        "Rate limit exceeded, waiting",
                        retry_after=retry_after,
                        attempt=attempt + 1,
                    )
                    time.sleep(retry_after)
                    continue

                # Handle authentication errors
                if response.status_code == 401:
                    self._authenticated = False
                    self._ensure_authenticated()
                    continue

                # Handle other errors
                if response.status_code >= 400:
                    raise APIError(
                        message=f"API error: {response.status_code}",
                        platform=self.platform_name,
                        details={
                            "status_code": response.status_code,
                            "response": response.text,
                        },
                    )

                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                self.logger.warning(
                    "Request timeout, retrying",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                )
                time.sleep(2**attempt)  # Exponential backoff

            except httpx.RequestError as e:
                last_error = e
                self.logger.warning(
                    "Request error, retrying",
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                )
                time.sleep(2**attempt)

        # All retries exhausted
        raise APIError(
            message=f"Request failed after {self.max_retries} retries",
            platform=self.platform_name,
            details={"last_error": str(last_error)},
        )

    def _paginate(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        page_size: int = 100,
        page_key: str = "page",
        size_key: str = "page_size",
        data_key: str = "data",
        total_key: str = "total",
    ) -> Generator[dict[str, Any], None, None]:
        """Generic pagination helper.

        Args:
            endpoint: API endpoint to paginate.
            params: Base query parameters.
            page_size: Number of items per page.
            page_key: Parameter name for page number.
            size_key: Parameter name for page size.
            data_key: Response key containing data items.
            total_key: Response key containing total count.

        Yields:
            Individual data records.
        """
        params = params or {}
        params[size_key] = page_size
        page = 1
        total_fetched = 0

        while True:
            params[page_key] = page
            response = self._request("GET", endpoint, params=params)

            items = response.get(data_key, [])
            if not items:
                break

            for item in items:
                yield item
                total_fetched += 1

            # Check if we've fetched all items
            total = response.get(total_key)
            if total is not None and total_fetched >= total:
                break

            # Check if this was the last page
            if len(items) < page_size:
                break

            page += 1

        self.logger.info(
            "Pagination complete",
            endpoint=endpoint,
            total_fetched=total_fetched,
        )

    def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        if self._client is not None:
            self._client.close()
            self._client = None
        self._authenticated = False

    def __enter__(self) -> "BaseExtractor":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
