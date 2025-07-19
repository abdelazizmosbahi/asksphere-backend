import logging
from detoxify import Detoxify

logger = logging.getLogger(__name__)

class AIContentFilter:
    def __init__(self, modelVersion):
        logger.info(f"Initializing AIContentFilter with modelVersion={modelVersion}")
        self.modelVersion = modelVersion
        self.model = None

    def filterContent(self, content, memberId, questionId, answerId, communityId, db):
        try:
            if self.model is None:
                logger.info("Loading Detoxify model")
                self.model = Detoxify(self.modelVersion)
                logger.info("Detoxify model loaded")
            # Rest of the code...
        except Exception as e:
            logger.error(f"Error in filterContent: {str(e)}")
            raise