from detoxify import Detoxify
import logging

class AIContentFilter:
    def __init__(self):
        self.model = None
    def load_model(self):
        if self.model is None:
            logging.info("Loading Detoxify model")
            self.model = Detoxify('original')
    def predict(self, text):
        self.load_model()
        return self.model.predict(text)