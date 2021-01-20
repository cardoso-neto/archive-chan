"""
Adapted from:
https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/

"""
from typing import Optional

from requests import PreparedRequest, Response, Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, timeout: int = 10, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(
        self, request: PreparedRequest, timeout: Optional[int] = None, **kwargs
    ) -> Response:
        if timeout is None:
            kwargs["timeout"] = self.timeout
        else:
            kwargs["timeout"] = timeout
        return super().send(request, **kwargs)


class RetrySession(Session):
    def __init__(self, max_retries: int = 3, timeout: int = 16) -> None:
        super().__init__()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[413, 429, 500, 502, 503, 504],
        )
        adapter = TimeoutHTTPAdapter(timeout=timeout, max_retries=retry_strategy)
        self.mount("https://", adapter)
        self.mount("http://", adapter)
