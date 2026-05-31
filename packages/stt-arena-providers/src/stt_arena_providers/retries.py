from __future__ import annotations

import ssl
from collections.abc import Iterator

import httpx

from stt_arena_providers.settings import ProviderSettings

RETRYABLE_HTTP_STATUS_CODES = {408, 409, 425, 429}
RETRYABLE_EXCEPTION_NAMES = {
    "Aborted",
    "DeadlineExceeded",
    "GatewayTimeout",
    "InternalServerError",
    "ResourceExhausted",
    "RetryError",
    "ServiceUnavailable",
    "TooManyRequests",
}
MAX_ERROR_DETAIL_LENGTH = 1000


def retry_delay_sec(settings: ProviderSettings, failed_attempt: int) -> float:
    base_delay = max(0.0, float(settings.provider_retry_base_delay_sec))
    max_delay = max(base_delay, float(settings.provider_retry_max_delay_sec))
    return min(max_delay, base_delay * (2 ** max(0, failed_attempt - 1)))


def is_retryable_exception(exc: BaseException) -> bool:
    for item in _exception_chain(exc):
        if isinstance(item, httpx.HTTPStatusError):
            return is_retryable_http_status(item.response.status_code)
        if isinstance(
            item,
            (TimeoutError, ConnectionError, ssl.SSLError, httpx.TransportError),
        ):
            return True
        if item.__class__.__name__ in RETRYABLE_EXCEPTION_NAMES:
            return True

        status_code = getattr(item, "status_code", None)
        if isinstance(status_code, int) and is_retryable_http_status(status_code):
            return True
    return False


def is_retryable_http_status(status_code: int) -> bool:
    return status_code in RETRYABLE_HTTP_STATUS_CODES or status_code >= 500


def exception_message(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        body = exc.response.text.strip()
        if body:
            return _truncate(body)
    return _truncate(str(exc).strip() or exc.__class__.__name__)


def exception_detail(exc: BaseException) -> str:
    status_code = _status_code(exc)
    status_detail = f" status_code={status_code}" if status_code is not None else ""
    return (
        f"{exc.__class__.__module__}.{exc.__class__.__name__}"
        f"{status_detail}: {exception_message(exc)}"
    )


def _status_code(exc: BaseException) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    status_code = getattr(exc, "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _exception_chain(exc: BaseException) -> Iterator[BaseException]:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _truncate(value: str) -> str:
    if len(value) <= MAX_ERROR_DETAIL_LENGTH:
        return value
    return f"{value[:MAX_ERROR_DETAIL_LENGTH]}..."
