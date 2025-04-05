from flask_login import UserMixin
from datetime import datetime, timedelta
from bson import ObjectId
from detoxify import Detoxify
from sentence_transformers import SentenceTransformer, util

class User:
    def __init__(self, id, username, password, avatar=None):
        self.id = id
        self.username = username
        self.password = password
        self.avatar = avatar if avatar else "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

class Notification:
    def __init__(self, id, memberId, message, type, relatedId=None, read=False, dateCreated=None):
        self.id = id
        self.memberId = memberId
        self.message = message
        self.type = type  # e.g., "answer", "inappropriate", "badge", "ban", "warning", "vote"
        self.relatedId = relatedId  # e.g., questionId, answerId, badge name
        self.read = read
        self.dateCreated = dateCreated if dateCreated else datetime.utcnow()

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

    def createNotification(self, message, type, relatedId, db):
        notification = Notification(
            id=None,
            memberId=ObjectId(self.id),
            message=message,
            type=type,
            relatedId=relatedId,
            read=False
        )
        db.notifications.insert_one({
            "memberId": notification.memberId,
            "message": notification.message,
            "type": notification.type,
            "relatedId": relatedId,
            "read": notification.read,
            "dateCreated": notification.dateCreated
        })

# Rest of the classes (Community, Question, Answer, Vote, Member_Community, AIContentFilter, CommunityValidator) remain unchanged
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
            {"$set": {"content": content}}
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
            
            if toxicity_score > 0.9:
                keys = [key for key, value in results.items() if value > 0.5 and key != 'toxicity']
                print(f"Inappropriate content detected. Keys: {keys}")
                # Log the inappropriate attempt
                db.inappropriate_content.insert_one({
                    "memberId": memberId,
                    "questionId": questionId,
                    "answerId": answerId,
                    "communityId": communityId,
                    "content": content,
                    "keys": keys,
                    "date": datetime.utcnow()
                })

                # Increment the user's restrictionLevel
                user = db.users.find_one({"_id": memberId})
                current_restriction_level = user.get("restrictionLevel", 0) + 1
                db.users.update_one(
                    {"_id": memberId},
                    {"$set": {"restrictionLevel": current_restriction_level}}
                )

                # Check the number of inappropriate attempts in this community
                inappropriate_count = db.inappropriate_content.count_documents({
                    "memberId": memberId,
                    "communityId": communityId
                })

                # Fetch the member object to create a notification
                member = db.users.find_one({"_id": memberId})
                if member:
                    member_obj = Member(
                        str(member['_id']),
                        member['username'],
                        member['email'],
                        member['password'],
                        member.get('dateJoined'),
                        member.get('reputation', 0),
                        member.get('status', 'active'),
                        member.get('restrictionLevel', 0),
                        member.get('badges', []),
                        member.get('avatar'),
                        member.get('community_interactions', {}),
                        member.get('community_bans', {})
                    )

                    # Ban from the community after 5 inappropriate attempts
                    if inappropriate_count >= 5:
                        ban_info = user.get("community_bans", {}).get(str(communityId), {})
                        ban_count = ban_info.get("ban_count", 0) if isinstance(ban_info, dict) else 0
                        ban_count += 1
                        ban_duration_days = ban_count
                        ban_expiration = datetime.utcnow() + timedelta(days=ban_duration_days)

                        db.users.update_one(
                            {"_id": memberId},
                            {"$set": {
                                f"community_bans.{communityId}": {
                                    "status": "banned",
                                    "ban_count": ban_count,
                                    "duration_days": ban_duration_days,
                                    "expiration": ban_expiration
                                }
                            }}
                        )

                        db.inappropriate_content.delete_many({
                            "memberId": memberId,
                            "communityId": communityId
                        })

                        db.moderation_logs.insert_one({
                            "memberId": memberId,
                            "communityId": communityId,
                            "reason": f"Banned from community for {ban_duration_days} day(s) due to 5 inappropriate attempts (Ban #{ban_count})",
                            "date": datetime.utcnow()
                        })

                        # Notify the user of the ban
                        member_obj.createNotification(
                            message=f"You have been banned from community {communityId} for {ban_duration_days} day(s) due to inappropriate content. Ban expires on {ban_expiration}.",
                            type="ban",
                            relatedId=str(communityId),
                            db=db
                        )

                        return "inappropriate content detected", f"You have been banned from this community for {ban_duration_days} day(s). Ban expires on {ban_expiration}."

                    attempts_left = 5 - inappropriate_count
                    if inappropriate_count == 3:
                        db.moderation_logs.insert_one({
                            "memberId": memberId,
                            "communityId": communityId,
                            "reason": "Warning: 3 inappropriate attempts detected in community",
                            "date": datetime.utcnow()
                        })
                        # Notify the user of the warning
                        member_obj.createNotification(
                            message="Warning: You have made 3 inappropriate attempts in this community. 2 more attempts will result in a ban.",
                            type="warning",
                            relatedId=str(communityId),
                            db=db
                        )
                        return "inappropriate content detected", "Warning: You will be banned from this community if you reach 5 inappropriate attempts (2 attempts left)."
                    elif attempts_left > 0:
                        # Notify the user of the inappropriate content
                        member_obj.createNotification(
                            message=f"Your content was flagged as inappropriate. You have {attempts_left} attempts left before a ban in community {communityId}.",
                            type="inappropriate",
                            relatedId=questionId if questionId else answerId,
                            db=db
                        )
                        return "inappropriate content detected", f"You have {attempts_left} attempts left."
                    else:
                        return "inappropriate content detected", "You have been banned from this community."

            return content, None

        except Exception as e:
            print(f"Error in filterContent: {str(e)}")
            raise e

    def reportUser(self, memberId, reason, db):
        db.moderation_logs.insert_one({
            "memberId": memberId,
            "reason": reason,
            "date": datetime.utcnow()
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
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.db = db
        self.description_embeddings = {}
        self.community_info = {}
        communities = self.db.communities.find()
        for community in communities:
            community_id = str(community['_id'])
            description = community['description']
            self.description_embeddings[community_id] = self.model.encode(description, convert_to_tensor=True)
            self.community_info[community_id] = {
                "name": community['name'],
                "description": description
            }

    def validate_content(self, content, community_id):
        content_embedding = self.model.encode(content, convert_to_tensor=True)
        community_id_str = str(community_id)
        if community_id_str not in self.description_embeddings:
            return None

        description_embedding = self.description_embeddings[community_id_str]
        similarity_score = util.cos_sim(content_embedding, description_embedding)[0][0].item()
        threshold = 0.12  # Current threshold
        is_relevant = similarity_score >= threshold

        # Debug logging
        print(f"Content: {content}")
        print(f"Target Community ID: {community_id_str}, Name: {self.community_info[community_id_str]['name']}, Description: {self.community_info[community_id_str]['description']}")
        print(f"Similarity Score: {similarity_score}, Threshold: {threshold}, Is Relevant: {is_relevant}")

        best_community = None
        best_score = similarity_score
        for comm_id, desc_embedding in self.description_embeddings.items():
            score = util.cos_sim(content_embedding, desc_embedding)[0][0].item()
            print(f"Community ID: {comm_id}, Name: {self.community_info[comm_id]['name']}, Score: {score}")
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

        similar_questions = []
        if is_relevant:
            questions = self.db.questions.find({"communityId": int(community_id)})
            for question in questions:
                question_text = question["title"] + " " + question["content"]
                question_embedding = self.model.encode(question_text, convert_to_tensor=True)
                question_score = util.cos_sim(content_embedding, question_embedding)[0][0].item()
                if question_score >= 0.3:
                    similar_questions.append({
                        "id": str(question["_id"]),
                        "title": question["title"],
                        "content": question["content"],
                        "similarity_score": question_score
                    })
            similar_questions = sorted(similar_questions, key=lambda x: x["similarity_score"], reverse=True)[:3]

        return {
            "is_relevant": is_relevant,
            "similarity_score": similarity_score,
            "suggested_community": suggested_community,
            "similar_questions": similar_questions
        }