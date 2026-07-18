"""将旧演示商品安全迁移为茶叶销售目录。"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from database.connection import get_db_context
from database.models import Category, Product, ProductDifficulty, ProductStatus


CATEGORY_SPECS = [
    ("绿茶", "清香鲜爽、注重嫩度与时令的非发酵茶", "leaf", 1),
    ("红茶", "香甜醇和、适合日常饮用与礼赠的全发酵茶", "cup", 2),
    ("乌龙茶", "香气层次丰富、滋味醇厚的半发酵茶", "mountain", 3),
    ("白茶", "工艺自然、毫香清甜的轻微发酵茶", "sunny", 4),
    ("普洱茶", "越陈越香、口感醇滑的后发酵茶", "collection", 5),
    ("花茶", "茶香与花香融合、清雅怡人的再加工茶", "flower", 6),
]

LEGACY_CATEGORY_NAMES = ["计算机类", "电子类", "管理类"]

TEA_PRODUCTS = [
    {
        "legacy_title": "基于Vue3的在线商城系统",
        "title": "明前特级西湖龙井 250g",
        "description": "产自浙江杭州核心产区，外形扁平挺秀，豆香清雅，茶汤嫩绿明亮，入口鲜爽回甘。建议使用85℃左右水温冲泡。",
        "price": 26800,
        "original_price": 32800,
        "tags": ["浙江杭州", "豆香", "鲜爽", "炒青绿茶"],
        "taste": ProductDifficulty.EASY,
        "category": "绿茶",
        "view_count": 1834,
        "sales_count": 326,
        "rating": 490,
        "review_count": 186,
    },
    {
        "legacy_title": "Python数据分析系统",
        "title": "洞庭碧螺春一级春茶 250g",
        "description": "产自江苏苏州太湖产区，条索纤细卷曲，花果香明显，滋味鲜醇柔和。适合偏爱清香型绿茶的顾客日常品饮。",
        "price": 19800,
        "original_price": 24800,
        "tags": ["江苏苏州", "花果香", "鲜醇", "卷曲绿茶"],
        "taste": ProductDifficulty.EASY,
        "category": "绿茶",
        "view_count": 1260,
        "sales_count": 218,
        "rating": 475,
        "review_count": 124,
    },
    {
        "legacy_title": "React Native移动应用",
        "title": "武夷金骏眉特级红茶 250g",
        "description": "精选福建武夷山原料制作，蜜香与花香协调，茶汤金黄透亮，滋味甘醇顺滑。适合自饮，也适合作为节日礼赠。",
        "price": 32800,
        "original_price": 39800,
        "tags": ["福建武夷山", "蜜香", "甘醇", "全发酵"],
        "taste": ProductDifficulty.MEDIUM,
        "category": "红茶",
        "view_count": 2350,
        "sales_count": 408,
        "rating": 492,
        "review_count": 236,
    },
    {
        "legacy_title": "企业人事管理系统",
        "title": "武夷山大红袍岩茶 250g",
        "description": "武夷岩茶经典品种，焙火香沉稳，茶汤橙黄明亮，入口醇厚并带有明显岩韵。适合喜欢浓郁香气和耐泡口感的茶友。",
        "price": 23800,
        "original_price": 29800,
        "tags": ["武夷岩茶", "焙火香", "岩韵", "半发酵"],
        "taste": ProductDifficulty.HARD,
        "category": "乌龙茶",
        "view_count": 1988,
        "sales_count": 305,
        "rating": 486,
        "review_count": 175,
    },
    {
        "legacy_title": "智能家居控制系统",
        "title": "安溪铁观音清香型 250g",
        "description": "产自福建安溪，兰花香清晰，茶汤黄绿明亮，滋味清鲜并带回甘。适合初次接触乌龙茶及偏爱高香茶品的顾客。",
        "price": 16800,
        "original_price": 21800,
        "tags": ["福建安溪", "兰花香", "清鲜", "半发酵"],
        "taste": ProductDifficulty.MEDIUM,
        "category": "乌龙茶",
        "view_count": 1568,
        "sales_count": 287,
        "rating": 478,
        "review_count": 146,
    },
    {
        "legacy_title": "微信小程序商城",
        "title": "福鼎白牡丹白茶 300g",
        "description": "选用福建福鼎春季原料，芽叶舒展，毫香与清甜感突出，茶汤柔和。适合日常慢饮，也便于家庭存放。",
        "price": 21800,
        "original_price": 26800,
        "tags": ["福建福鼎", "毫香", "清甜", "轻微发酵"],
        "taste": ProductDifficulty.EASY,
        "category": "白茶",
        "view_count": 1426,
        "sales_count": 196,
        "rating": 481,
        "review_count": 118,
    },
    {
        "legacy_title": "在线教育平台",
        "title": "新会陈皮普洱熟茶 357g",
        "description": "云南普洱熟茶与新会陈皮搭配，陈香与柑香协调，茶汤红浓醇滑，适合偏爱温润浓醇口感的顾客。",
        "price": 29800,
        "original_price": 36800,
        "tags": ["云南勐海", "新会陈皮", "陈香", "后发酵"],
        "taste": ProductDifficulty.HARD,
        "category": "普洱茶",
        "view_count": 2248,
        "sales_count": 364,
        "rating": 488,
        "review_count": 203,
    },
    {
        "legacy_title": "图书管理系统",
        "title": "横州茉莉银针花茶 250g",
        "description": "选用广西横州茉莉鲜花多次窨制，花香鲜灵持久，茶汤清亮柔和。适合喜欢清雅花香和轻盈口感的顾客。",
        "price": 13800,
        "original_price": 17800,
        "tags": ["广西横州", "茉莉花香", "清雅", "多次窨制"],
        "taste": ProductDifficulty.EASY,
        "category": "花茶",
        "view_count": 1186,
        "sales_count": 246,
        "rating": 472,
        "review_count": 132,
    },
]


def ensure_categories(session):
    categories = {}
    for name, description, icon, sort_order in CATEGORY_SPECS:
        category = session.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
        if category is None:
            category = Category(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                icon=icon,
                sort_order=sort_order,
            )
            session.add(category)
            session.flush()
        else:
            category.description = description
            category.icon = icon
            category.sort_order = sort_order
        categories[name] = category
    return categories


def migrate_products(session, categories):
    migrated = 0
    for spec in TEA_PRODUCTS:
        product = session.execute(
            select(Product).where(Product.title.in_([spec["legacy_title"], spec["title"]]))
        ).scalars().first()
        if product is None:
            continue

        product.title = spec["title"]
        product.description = spec["description"]
        product.price = spec["price"]
        product.original_price = spec["original_price"]
        product.cover_image = None
        product.tech_stack = spec["tags"]
        product.difficulty = spec["taste"]
        product.status = ProductStatus.PUBLISHED
        product.category_id = categories[spec["category"]].id
        product.view_count = spec["view_count"]
        product.sales_count = spec["sales_count"]
        product.rating = spec["rating"]
        product.review_count = spec["review_count"]
        migrated += 1
    return migrated


def remove_unused_legacy_categories(session):
    """仅删除已无商品引用的旧演示分类。"""
    removed = 0
    legacy_categories = session.execute(
        select(Category).where(Category.name.in_(LEGACY_CATEGORY_NAMES))
    ).scalars().all()
    for category in legacy_categories:
        referenced_product = session.execute(
            select(Product.id).where(Product.category_id == category.id).limit(1)
        ).scalar_one_or_none()
        if referenced_product is None:
            session.delete(category)
            removed += 1
    return removed


def main():
    with get_db_context() as session:
        categories = ensure_categories(session)
        migrated = migrate_products(session, categories)
        removed_categories = remove_unused_legacy_categories(session)
        print(f"茶叶分类已就绪：{len(categories)} 个")
        print(f"演示商品已迁移：{migrated} 个")
        print(f"旧演示分类已清理：{removed_categories} 个")


if __name__ == "__main__":
    main()
