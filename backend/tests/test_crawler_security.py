from unittest.mock import patch

import pytest

from backend.crawler.framework.url_policy import UnsafeCrawlerURL, validate_crawler_url


PUBLIC_DNS = [(2, 1, 6, "", ("103.163.210.129", 443))]


@patch("backend.crawler.framework.url_policy.socket.getaddrinfo", return_value=PUBLIC_DNS)
def test_procurement_hosts_are_allowed(_resolver):
    assert validate_crawler_url("https://www.eprocure.gov.bd/TenderDetailsServlet")
    assert validate_crawler_url("https://www.bppa.gov.bd/path")


@pytest.mark.parametrize(
    "url",
    [
        "http://www.eprocure.gov.bd/path",
        "https://localhost/path",
        "https://127.0.0.1/path",
        "https://user:pass@www.eprocure.gov.bd/path",
        "https://www.eprocure.gov.bd:8443/path",
        "https://example.com/path",
    ],
)
def test_untrusted_urls_are_rejected(url):
    with pytest.raises(UnsafeCrawlerURL):
        validate_crawler_url(url)


@patch(
    "backend.crawler.framework.url_policy.socket.getaddrinfo",
    return_value=[(2, 1, 6, "", ("127.0.0.1", 443))],
)
def test_dns_rebinding_to_private_address_is_rejected(_resolver):
    with pytest.raises(UnsafeCrawlerURL):
        validate_crawler_url("https://www.eprocure.gov.bd/path")
