from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from datetime import datetime
from flask_cors import CORS  # Import CORS
from app.utils.ai_content_filter import AIContentFilter  # Import the AIContentFilter class
app = Flask(__name__)
app.config['SECRET_KEY'] = '9035aa297aca23fca3b5f070fe909e01567739b99fa41a55bb6ad63076a0adf9'
app.config['MONGO_URI'] = 'mongodb+srv://mosbehiasiz:BSvss3YfLyb0ojMa@cluster0.ntfhykc.mongodb.net/asksphere?retryWrites=true&w=majority'
CORS(app, resources={r"/*": {"origins": "http://localhost:4200"}}, supports_credentials=True)

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

    # Initialize extensions
    mongo.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

# Register blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app