from database.connection import db_session
from services.product_service import ProductService

def test():
    with db_session() as db:
        service = ProductService(db)
        # Try to get the first product
        product = service.get_product("dfab8bf9-3135-4abc-9e65-473b1304a513", increment_view=True)
        print(f"Product: {product}")

test()
