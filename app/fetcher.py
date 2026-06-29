import asyncio
from typing import Callable, Dict, List, Optional, Tuple

from curl_cffi.requests import AsyncSession


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

BASE_URL = "https://market.yandex.ru/search"


class Fetcher:
    def __init__(
        self,
        cookies: Dict[str, str],
        concurrency: int = 3,
        delay: float = 0.5,
        timeout: int = 30,
    ):
        self.cookies = cookies
        self.concurrency = concurrency
        self.delay = delay
        self.timeout = timeout

    async def _fetch_one(
        self,
        session: AsyncSession,
        semaphore: asyncio.Semaphore,
        params: Dict,
        page: int,
        page_callback: Optional[Callable[[int, Optional[str]], None]] = None,
    ) -> Tuple[int, Optional[str]]:
        async with semaphore:
            html: Optional[str] = None
            try:
                r = await session.get(
                    BASE_URL,
                    params={**params, "page": page},
                    headers=HEADERS,
                    cookies=self.cookies,
                    impersonate="chrome110",
                    timeout=self.timeout,
                )
                await asyncio.sleep(self.delay)
                if r.status_code == 200:
                    html = r.text
                else:
                    print(f"⚠️ Страница {page}: статус {r.status_code}")
            except Exception as e:
                print(f"⚠️ Страница {page}: {e}")

        # Вызываем callback сразу после освобождения семафора —
        # пока остальные задачи уже могут начать следующий запрос
        if page_callback:
            page_callback(page, html)

        return page, html

    async def fetch_pages(
        self,
        params: Dict,
        pages: int,
        start_page: int = 1,
        page_callback: Optional[Callable[[int, Optional[str]], None]] = None,
    ) -> List[Tuple[int, Optional[str]]]:
        semaphore = asyncio.Semaphore(self.concurrency)
        async with AsyncSession() as session:
            tasks = [
                self._fetch_one(session, semaphore, params, p, page_callback)
                for p in range(start_page, start_page + pages)
            ]
            results = await asyncio.gather(*tasks)
        return sorted(results)