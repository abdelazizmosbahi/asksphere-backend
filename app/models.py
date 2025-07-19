from flask_login import UserMixin
from datetime import datetime, timedelta
from bson import ObjectId
from detoxify import Detoxify
from sentence_transformers import SentenceTransformer, util
import logging
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

logger = logging.getLogger(__name__)
class User:
    def __init__(self, id, username, password, avatar=None):
        self.id = id
        self.username = username
        self.password = password
        self.avatar = avatar if avatar else "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

class Notification:
    def __init__(self, id, memberId, message, type, relatedId=None, read=False, createdAt=None, communityId=None):
        self.id = id
        self.memberId = memberId
        self.message = message
        self.type = type  # e.g., "answer", "inappropriate", "badge", "ban", "warning", "vote"
        self.relatedId = relatedId  # e.g., questionId, answerId, badge name
        self.read = read
        self.createdAt = createdAt if createdAt else datetime.utcnow()
        self.communityId = communityId

class Member(UserMixin):
    def __init__(self, id, username, email, password, dateJoined, reputation, status, restrictionLevel, badges, avatar=None, community_interactions=None, community_bans=None):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.dateJoined = dateJoined
        self.reputation = reputation
        self.status = status
        self.restrictionLevel = restrictionLevel
        self.badges = badges if badges else []
        self.avatar = avatar if avatar else "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        self.community_interactions = community_interactions if community_interactions else {}
        self.community_bans = community_bans if community_bans else {}

    def get_id(self):
        return self.id

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.status != 'banned'

    @property
    def is_anonymous(self):
        return False
    
    def editProfile(self, email, username=None):
        self.email = email
        if username:
            self.username = username
    
    def changePassword(self, new_password):
        self.password = new_password

    def award_badge(self, badge_name):
        if badge_name not in self.badges:
            self.badges.append(badge_name)

    def askQuestion(self, title, content, communityId):
        return Question(None, title, content, datetime.utcnow(), communityId)

    def answerQuestion(self, content, questionId):
        return Answer(None, content, datetime.utcnow(), ObjectId(self.id), questionId, 0)

    def voteQuestion(self, questionId, value):
        return Vote(None, value, ObjectId(self.id), questionId, None)

    def voteAnswer(self, answerId, value):
        return Vote(None, value, ObjectId(self.id), None, answerId)

    def viewBadges(self):
        return self.badges

    def viewScore(self):
        return self.reputation

    def awardBadge(self, badge, db):
        if badge not in self.badges:
            self.badges.append(badge)
            db.users.update_one(
                {"_id": ObjectId(self.id)},
                {"$set": {"badges": self.badges}}
            )
            # Create a notification for the new badge
            self.createNotification(
                message=f"You earned a new badge: {badge}!",
                type="badge",
                relatedId=badge,
                db=db
            )

    def trackInteraction(self, communityId, interaction_type, db):
        if str(communityId) not in self.community_interactions:
            self.community_interactions[str(communityId)] = {
                "questions": 0,
                "answers": 0,
                "votes": 0,
                "total": 0
            }

        self.community_interactions[str(communityId)][interaction_type] += 1
        self.community_interactions[str(communityId)]["total"] += 1

        db.users.update_one(
            {"_id": ObjectId(self.id)},
            {"$set": {f"community_interactions.{str(communityId)}": self.community_interactions[str(communityId)]}}
        )

        community_name = db.communities.find_one({"_id": int(communityId)})["name"]
        badge_prefix = self.getBadgePrefix(community_name)

        if self.community_interactions[str(communityId)]["total"] >= 10:
            self.awardBadge(f"{badge_prefix} Top Contributor", db)

        if self.community_interactions[str(communityId)]["questions"] >= 5:
            self.awardBadge(f"{badge_prefix} Asker", db)

        if self.community_interactions[str(communityId)]["answers"] >= 5:
            self.awardBadge(f"{badge_prefix} Questioner", db)

    def getBadgePrefix(self, community_name):
        badge_mapping = {
            "Development": "Developer",
            "Gaming": "Gamer",
            "Music": "Musician",
            "Science": "Scientist",
            "Art": "Artist",
            "Sports": "Athlete"
        }
        return badge_mapping.get(community_name, "Member")

    def createNotification(self, message, type, relatedId, db, communityId=None):
        notification = Notification(
            id=None,
            memberId=ObjectId(self.id),
            message=message,
            type=type,
            relatedId=relatedId,
            read=False,
            communityId=communityId
        )
        db.notifications.insert_one({
            "memberId": notification.memberId,
            "message": notification.message,
            "type": notification.type,
            "relatedId": relatedId,
            "read": notification.read,
            "createdAt": notification.createdAt,
            "communityId": notification.communityId
        })

class Community:
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description

class Question:
    def __init__(self, id, title, content, dateCreated, communityId):
        self.id = id
        self.title = title
        self.content = content
        self.dateCreated = dateCreated
        self.communityId = communityId

    def deleteQuestion(self, db):
        db.questions.delete_one({"_id": ObjectId(self.id)})
        db.answers.delete_many({"questionId": ObjectId(self.id)})
        db.votes.delete_many({"questionId": ObjectId(self.id)})

class Answer:
    def __init__(self, id, content, dateCreated, memberId, questionId, score):
        self.id = id
        self.content = content
        self.dateCreated = dateCreated
        self.memberId = memberId
        self.questionId = questionId
        self.score = score

    def deleteAnswer(self, db):
        db.answers.delete_one({"_id": ObjectId(self.id)})
        db.votes.delete_many({"answerId": ObjectId(self.id)})

    def updateAnswer(self, content, db):
        self.content = content
        db.answers.update_one(
            {"_id": ObjectId(self.id)},
            {"$set": {"content": content, "dateUpdated": datetime.utcnow()}}
        )

class Vote:
    def __init__(self, id, value, memberId, questionId, answerId):
        self.id = id
        self.value = value
        self.memberId = memberId
        self.questionId = questionId
        self.answerId = answerId

class Member_Community:
    def __init__(self, memberId, communityId, dateJoined):
        self.memberId = memberId
        self.communityId = communityId
        self.dateJoined = dateJoined

    def joinCommunity(self, memberId, communityId, db):
        db.member_communities.insert_one({
            "memberId": memberId,
            "communityId": communityId,
            "dateJoined": self.dateJoined
        })

    def leaveCommunity(self, memberId, communityId, db):
        db.member_communities.delete_one({
            "memberId": memberId,
            "communityId": communityId
        })

class AIContentFilter:
    def __init__(self, modelVersion):
        self.modelVersion = modelVersion
        self.model = Detoxify('original')

    def filterContent(self, content, memberId, questionId, answerId, communityId, db):
        print(f"Filtering content: {content}")
        print(f"MemberId: {memberId}, QuestionId: {questionId}, AnswerId: {answerId}, CommunityId: {communityId}")
        try:
            results = self.model.predict(content)
            print(f"Detoxify results: {results}")
            toxicity_score = results['toxicity']
            
            if toxicity_score > 0.5:  # Aligned with routes.py threshold
                keys = [key for key, value in results.items() if value > 0.5 and key != 'toxicity']
                print(f"Inappropriate content detected. Keys: {keys}")
                # Log to inappropriate_content
                db.inappropriate_content.insert_one({
                    "content": content,
                    "memberId": memberId,
                    "communityId": communityId,
                    "questionId": questionId,
                    "answerId": answerId,
                    "timestamp": datetime.utcnow(),
                    "keys": keys or ["toxicity"],
                    "isProcessed": False
                })
                # Increment restrictionLevel
                user = db.users.find_one({"_id": memberId})
                restriction_level = (user.get('restrictionLevel', 0) or 0) + 1
                db.users.update_one(
                    {"_id": memberId},
                    {"$set": {"restrictionLevel": restriction_level}}
                )
                # Create notification
                attempts_left = 5 - restriction_level
                feedback = f"You have {attempts_left} attempts left before a ban in community {communityId}."
                if attempts_left <= 2 and attempts_left > 0:
                    feedback = f"Warning: You will be banned from this community if you reach 5 inappropriate attempts ({attempts_left} attempts left)."
                elif attempts_left <= 0:
                    ban_duration_days = 1
                    ban_expires = datetime.utcnow() + timedelta(days=ban_duration_days)
                    db.community_bans.insert_one({
                        "memberId": memberId,
                        "communityId": communityId,
                        "startDate": datetime.utcnow(),
                        "expiresAt": ban_expires,
                        "reason": "Exceeded inappropriate content attempts"
                    })
                    # Clear inappropriate_content for this user and community
                    db.inappropriate_content.delete_many({
                        "memberId": memberId,
                        "communityId": communityId
                    })
                    feedback = f"You have been banned from this community for {ban_duration_days} day(s). Ban expires on {ban_expires.isoformat()}."
                    db.users.update_one(
                        {"_id": memberId},
                        {"$set": {"restrictionLevel": 0}}
                    )
                
                # Notify the user
                db.notifications.insert_one({
                    "memberId": memberId,
                    "type": "inappropriate",
                    "message": feedback,
                    "isRead": False,
                    "createdAt": datetime.utcnow(),
                    "communityId": communityId
                })
                return content, feedback

            return content, None

        except Exception as e:
            print(f"Error in filterContent: {str(e)}")
            raise e

    def reportUser(self, memberId, reason, db):
        db.moderation_logs.insert_one({
            "memberId": memberId,
            "reason": reason,
            "timestamp": datetime.utcnow()
        })

    def restrictMember(self, memberId, days, db):
        db.users.update_one(
            {"_id": memberId},
            {"$set": {"restrictionLevel": days}}
        )

    def banMember(self, memberId, db):
        db.users.update_one(
            {"_id": memberId},
            {"$set": {"status": "banned"}}
        )

class CommunityValidator:
    def __init__(self, db):
        logger.info("Initializing CommunityValidator")
        self.db = db
        self.model = None
        self.description_embeddings = {}
        self.community_info = {}
        self._load_community_info()

    def _load_community_info(self):
        """Load community information from the database without encoding."""
        try:
            logger.info("Loading community information from database")
            communities = self.db.communities.find()
            for community in communities:
                community_id = str(community['_id'])
                self.community_info[community_id] = {
                    "name": community['name'],
                    "description": community['description']
                }
            logger.info(f"Loaded {len(self.community_info)} communities")
        except Exception as e:
            logger.error(f"Failed to load community information: {str(e)}")
            raise

    def _load_model_and_embeddings(self):
        """Lazy-load the SentenceTransformer model and encode community descriptions."""
        if self.model is None:
            try:
                logger.info("Loading SentenceTransformer model 'all-mpnet-base-v2'")
                self.model = SentenceTransformer('all-mpnet-base-v2')
                logger.info("SentenceTransformer model loaded successfully")
                
                logger.info("Encoding community descriptions")
                for community_id, info in self.community_info.items():
                    description = info['description']
                    self.description_embeddings[community_id] = self.model.encode(description, convert_to_tensor=True)
                logger.info(f"Encoded embeddings for {len(self.description_embeddings)} communities")
            except Exception as e:
                logger.error(f"Failed to load model or encode embeddings: {str(e)}")
                raise

    def validate_content(self, content, community_id):
        """Validate content relevance to a community and find similar questions."""
        try:
            logger.info(f"Validating content for community ID: {community_id}")
            # Lazy-load model and embeddings
            self._load_model_and_embeddings()

            # Encode content
            logger.info("Encoding content")
            content_embedding = self.model.encode(content, convert_to_tensor=True)
            logger.info("Content encoded successfully")

            community_id_str = str(community_id)
            if community_id_str not in self.description_embeddings:
                logger.warning(f"Community ID {community_id_str} not found in embeddings")
                return None

            # Calculate similarity with target community
            description_embedding = self.description_embeddings[community_id_str]
            similarity_score = cos_sim(content_embedding, description_embedding)[0][0].item()
            threshold = 0.10
            is_relevant = similarity_score >= threshold

            logger.info(f"Content: {content}")
            logger.info(f"Target Community ID: {community_id_str}, Name: {self.community_info[community_id_str]['name']}, Description: {self.community_info[community_id_str]['description']}")
            logger.info(f"Similarity Score: {similarity_score}, Threshold: {threshold}, Is Relevant: {is_relevant}")

            # Find the best matching community
            best_community = None
            best_score = similarity_score
            for comm_id, desc_embedding in self.description_embeddings.items():
                score = cos_sim(content_embedding, desc_embedding)[0][0].item()
                logger.info(f"Community ID: {comm_id}, Name: {self.community_info[comm_id]['name']}, Score: {score}")
                if score > best_score:
                    best_score = score
                    best_community = comm_id

            suggested_community = None
            if not is_relevant and best_community and best_community != community_id_str:
                suggested_community = {
                    "id": int(best_community),
                    "name": self.community_info[best_community]["name"],
                    "similarity_score": best_score
                }
                logger.info(f"Suggested Community: ID {suggested_community['id']}, Name: {suggested_community['name']}, Score: {best_score}")

            # Find similar questions
            similar_questions = []
            if is_relevant:
                logger.info(f"Searching for similar questions in community ID: {community_id}")
                questions = self.db.questions.find({"communityId": int(community_id)})
                for question in questions:
                    question_text = question["title"] + " " + question["content"]
                    try:
                        question_embedding = self.model.encode(question_text, convert_to_tensor=True)
                        question_score = cos_sim(content_embedding, question_embedding)[0][0].item()
                        if question_score >= 0.3:
                            similar_questions.append({
                                "id": str(question["_id"]),
                                "title": question["title"],
                                "content": question["content"],
                                "similarity_score": question_score
                            })
                            logger.info(f"Found similar question ID: {str(question['_id'])}, Score: {question_score}")
                    except Exception as e:
                        logger.error(f"Error processing question ID {str(question['_id'])}: {str(e)}")
                similar_questions = sorted(similar_questions, key=lambda x: x["similarity_score"], reverse=True)[:3]
                logger.info(f"Found {len(similar_questions)} similar questions")

            return {
                "is_relevant": is_relevant,
                "similarity_score": similarity_score,
                "suggested_community": suggested_community,
                "similar_questions": similar_questions
            }
        except Exception as e:
            logger.error(f"Error in validate_content: {str(e)}")
            raise