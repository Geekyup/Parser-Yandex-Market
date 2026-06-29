import asyncio
import time

from app import Fetcher, extract_products, load_cookies, save_to_excel
from config import (
    CONCURRENCY,
    COOKIES_FILE,
    DEFAULT_PAGES,
    DELAY,
    OUTPUT_FILE,
    SEARCH_PARAMS,
    TIMEOUT,
)


async def run(pages: int) -> None:
    cookies = load_cookies(COOKIES_FILE)

    fetcher = Fetcher(cookies, concurrency=CONCURRENCY, delay=DELAY, timeout=TIMEOUT)

    print(f"\n🔍 Парсим {pages} страниц...")
    t0 = time.time()

    raw_pages = await fetcher.fetch_pages(SEARCH_PARAMS, pages)

    seen: set = set()
    products = []

    for page, html in raw_pages:
        if not html:
            continue
        new = []
        for p in extract_products(html):
            key = p["product_id"] or p["name"]
            if key not in seen:
                seen.add(key)
                new.append(p)
        if new:
            print(f"✅ Страница {page}: {len(new)} товаров")
        products.extend(new)

    print(f"\n{'='*50}")
    print(f"Итого: {len(products)} товаров за {time.time() - t0:.1f} сек")

    save_to_excel(products, OUTPUT_FILE)


def main() -> None:
    try:
        pages = int(input(f"Страниц для парсинга (по умолчанию {DEFAULT_PAGES}): ") or DEFAULT_PAGES)
    except ValueError:
        pages = DEFAULT_PAGES

    asyncio.run(run(pages))


if __name__ == "__main__":
    main()
