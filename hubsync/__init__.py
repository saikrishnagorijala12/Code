import os
from flask import Flask
from dotenv import load_dotenv

from .blueprints import register_routes


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') 
    register_routes(app)
    return app


