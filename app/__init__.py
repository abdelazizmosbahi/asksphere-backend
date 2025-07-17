from datetime import datetime
import os
from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
from app.utils.ai_content_filter import AIContentFilter
from app import routes
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
CORS(app, resources={r"/*": {"origins": "https://wonderful-sky-054cb711e.2.azurestaticapps.net"}}, supports_credentials=True)
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
ai_content_filter = AIContentFilter(modelVersion='original')
from app import routes

# Initialize the database with some sample data
def init_db():
    if mongo.db.users.count_documents({}) == 0:
        hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
        mongo.db.users.insert_one({
            "username": "testuser",
            "email": "testuser@example.com",
            "password": hashed_password,
            "dateJoined": datetime.utcnow(),
            "reputation": 0,
            "status": "active",
            "restrictionLevel": 0,
            "badges": [],
            "community_interactions": {},
            "community_bans": {}
        })

    if mongo.db.communities.count_documents({}) == 0:
        communities = [
            {"_id": 1, "name": "Development", "description": "A community for developers..."},
            {"_id": 2, "name": "Gaming", "description": "A community for gamers..."},
            {"_id": 3, "name": "Music", "description": "A community for music lovers..."},
            {"_id": 4, "name": "Science", "description": "A community for discussing scientific discoveries..."},
            {"_id": 5, "name": "Art", "description": "A community for artists..."},
            {"_id": 6, "name": "Sports", "description": "A community for sports enthusiasts..."}
        ]
        mongo.db.communities.insert_many(communities)

init_db()