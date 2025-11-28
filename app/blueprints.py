from app.routes.auth import auth_bp
from app.routes.domo import domo_bp

def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(domo_bp)