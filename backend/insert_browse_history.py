from database.connection import get_db_context
from database.models import User, Product, UserBrowseHistory
from sqlalchemy import select
import uuid

def main():
    with get_db_context() as db:
        user_result = db.execute(select(User).limit(1))
        user = user_result.scalars().first()
        if not user:
            print('没有用户')
            return
        print(f'用户: {user.id} - {user.username}')
        
        product_result = db.execute(select(Product).limit(5))
        products = product_result.scalars().all()
        print(f'商品数量: {len(products)}')
        
        for p in products:
            browse = UserBrowseHistory(
                id=str(uuid.uuid4()),
                user_id=user.id,
                product_id=p.id,
                view_duration=60,
            )
            db.add(browse)
            print(f'添加浏览: {p.title[:20]}...')
        
        db.commit()
        print('完成!')

main()
