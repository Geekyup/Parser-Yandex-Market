from typing import Dict, List

from openpyxl import Workbook


COLUMNS = [
    ("Название",  "name"),
    ("ID",        "product_id"),
    ("Цена",      "price"),
    ("Рейтинг",   "rating"),
    ("Отзывы",    "reviews"),
    ("Купили",    "purchases"),
    ("Ссылка",    "url"),
]


def save_to_excel(products: List[Dict], filename: str = "products.xlsx") -> None:
    if not products:
        print("❌ Нет данных для сохранения")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Товары"

    ws.append([col[0] for col in COLUMNS])
    for p in products:
        ws.append([p.get(key) for _, key in COLUMNS])

    for col in ws.columns:
        width = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(width + 2, 50)

    wb.save(filename)
    print(f"💾 Сохранено {len(products)} товаров → {filename}")
