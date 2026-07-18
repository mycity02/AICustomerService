"""Flask API blueprint assembly."""
from flask import Blueprint

from .admin import bp as admin_bp
from .auth import bp as auth_bp
from .browse import bp as browse_bp
from .cart import bp as cart_bp
from .chat import bp as chat_bp
from .favorites import bp as favorites_bp
from .files import bp as files_bp
from .gateway import bp as gateway_bp
from .knowledge import bp as knowledge_bp
from .orders import bp as orders_bp
from .products import bp as products_bp
from .refunds import bp as refunds_bp
from .reviews import bp as reviews_bp
from .tickets import bp as tickets_bp


api_bp = Blueprint("api", __name__, url_prefix="/api")

for blueprint in (
    auth_bp,
    chat_bp,
    tickets_bp,
    files_bp,
    admin_bp,
    knowledge_bp,
    products_bp,
    cart_bp,
    orders_bp,
    reviews_bp,
    favorites_bp,
    browse_bp,
    refunds_bp,
    gateway_bp,
):
    api_bp.register_blueprint(blueprint)


__all__ = ["api_bp"]
