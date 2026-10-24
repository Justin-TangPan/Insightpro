"""Keep imagery attached to the exact official source it came from."""
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


def first_source_image(html: str, source_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article") or soup.find("main")
    candidates = [node.get("src") or node.get("data-src") for node in article.select("img")] if article else []
    candidates += [node.get("content") for node in soup.select('meta[property="og:image"], meta[name="twitter:image"]')]
    for candidate in candidates:
        if not candidate or candidate.startswith("data:"):
            continue
        url = urljoin(source_url, candidate)
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.netloc and not parsed.username and not parsed.password and not parsed.path.lower().endswith(".svg"):
            return url
    return ""
