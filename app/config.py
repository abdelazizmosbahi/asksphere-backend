import os
from dotenv import load_dotenv

load_dotenv()

class Config:
       SECRET_KEY = os.getenv('SECRET_KEY', '79da288f9993304133b20b3d2bffaa03c59055605dbf3ac9383e1fb0a151a245')
       MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://mosbehiasiz:BSvss3YfLyb0ojMa@cluster0.ntfhykc.mongodb.net/asksphere?retryWrites=true&w=majority')