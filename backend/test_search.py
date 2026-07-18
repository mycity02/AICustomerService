from database.connection import get_db_context
from services.product_service import ProductService

def test():
    with get_db_context() as db:
        ps = ProductService(db)
        r = ps.search_products(keyword="python")
        products = r.get("products", [])
        print(f"找到 {len(products)} 个商品")
        for p in products[:3]:
            print(f"  - {p.get('title')[:30]} | tech_stack: {p.get('tech_stack')}")

test()
