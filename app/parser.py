import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup


def parse_product(block) -> Optional[Dict]:
    title = block.find("span", {"data-auto": "snippet-title"})
    if not title or not (name := title.get("title", "").strip()):
        return None

    link = block.find("a", {"data-auto": "snippet-link"}) or block.find(
        "a", {"data-auto": "galleryLink"}
    )
    url = link["href"] if link else ""
    if url and not url.startswith("http"):
        url = "https://market.yandex.ru" + url

    price_el = block.find("span", {"data-auto": "snippet-price-current"})
    price = price_el.get_text(strip=True) if price_el else None

    rating, reviews, purchases = None, None, None
    if r := block.find("span", {"data-auto": "reviews"}):
        text = r.get_text(strip=True)
        if m := re.search(r"([\d.]+)", text):
            rating = m.group(1)
        if m := re.search(r"\((\d+)\)", text):
            reviews = int(m.group(1))
        if m := re.search(r"(\d+)\s*купили", text):
            purchases = int(m.group(1))

    product_id = None
    if url and (m := re.search(r"/(?:product|card/[^/]+)/(\d+)", url)):
        product_id = m.group(1)

    return {
        "name": name,
        "product_id": product_id,
        "price": price,
        "rating": rating,
        "reviews": reviews,
        "purchases": purchases,
        "url": url,
    }


def extract_products(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.find_all("div", {"data-zone-name": "productSnippet"})
    return [p for block in blocks if (p := parse_product(block))]
