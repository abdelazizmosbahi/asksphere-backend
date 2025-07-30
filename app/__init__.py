import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from datetime import datetime
from flask_cors import CORS
from app.utils.ai_content_filter import AIContentFilter
import ssl
from waitress import serve

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
print(f"MONGO_URI: {os.getenv('MONGO_URI')}")
CORS(app, resources={r"/*": {"origins": ["https://wonderful-sky-054cb711e.2.azurestaticapps.net", "http://localhost:4200"]}})
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
ai_content_filter = AIContentFilter(modelVersion='original')
from app import routes

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
            {"_id": 1, "name": "Development", "description": "A community for developers to discuss programming languages, software development, coding tips, frameworks, tools, projects, and career advice"},
            {"_id": 2, "name": "Gaming", "description": "A community for gamers to discuss video games, gaming consoles, PC gaming, esports, strategies, tips, tricks, and experiences"},
            {"_id": 3, "name": "Music", "description": "A community for music lovers to discuss songs, artists, genres, music production, instruments, concerts, and music history"},
            {"_id": 4, "name": "Science", "description": "A community for discussing scientific discoveries, research, theories, experiments, physics, chemistry, biology, astronomy, and technology"},
            {"_id": 5, "name": "Art", "description": "A community for artists to share their work, techniques, styles, digital art, traditional art, photography, design, and creative inspiration"},
            {"_id": 6, "name": "Sports", "description": "A community for sports enthusiasts to discuss games, events, teams, athletes, fitness, training, sports strategies, and fan experiences"}
        ]
        mongo.db.communities.insert_many(communities)

init_db()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    mongo.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    return app

@app.route('/debug')
def debug():
    try:
        from detoxify import Detoxify
        from sentence_transformers import SentenceTransformer
        ai_models = "loaded"
    except Exception as e:
        ai_models = f"failed: {str(e)}"
    return jsonify({
        "status": "running",
        "env": dict(os.environ),
        "mongo_available": mongo.db is not None if 'mongo' in globals() else False,
        "ai_models": ai_models
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
def index():
    return "Welcome to Asksphere!"

if __name__ == '__main__':
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile='/app/asksphere-cert.pem', keyfile='/app/asksphere-key.pem')
    serve(app, host='0.0.0.0', port=int(os.getenv('PORT', 5000)), ssl_context=ssl_context)