from detoxify import Detoxify
from datetime import datetime, timedelta
from bson.objectid import ObjectId

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

                    return "inappropriate content detected", f"You have been banned from this community for {ban_duration_days} day(s). Ban expires on {ban_expiration}."

                attempts_left = 5 - inappropriate_count
                if inappropriate_count == 3:
                    db.moderation_logs.insert_one({
                        "memberId": memberId,
                        "communityId": communityId,
                        "reason": "Warning: 3 inappropriate attempts detected in community",
                        "date": datetime.utcnow()
                    })
                    return "inappropriate content detected", "Warning: You will be banned from this community if you reach 5 inappropriate attempts (2 attempts left)."
                elif attempts_left > 0:
                    return "inappropriate content detected", f"You have {attempts_left} attempts left."
                else:
                    return "inappropriate content detected", "You have been banned from this community."

            return content, None

        except Exception as e:
            print(f"Error in filterContent: {str(e)}")
            raise e