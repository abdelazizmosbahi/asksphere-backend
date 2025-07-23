import base64
from app import app, mongo, bcrypt, login_manager
from flask import Blueprint, json, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Member, Community, Question, Answer, Vote, Member_Community, AIContentFilter, CommunityValidator
from datetime import datetime, timedelta
from bson import ObjectId
from app import ai_content_filter
from . import mongo
routes = Blueprint('routes', __name__)

ai_filter = AIContentFilter(modelVersion="1.0")
community_validator = CommunityValidator(mongo.db)

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        community_bans = user_data.get('community_bans', {})
        updated_bans = community_bans.copy()
        for community_id, ban_info in community_bans.items():
            if isinstance(ban_info, dict) and ban_info.get('status') == "banned":
                expiration = ban_info.get('expiration')
                if expiration and datetime.utcnow() > expiration:
                    updated_bans[community_id] = {}
        if updated_bans != community_bans:
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"community_bans": updated_bans}}
            )
            user_data['community_bans'] = updated_bans

        return Member(
            str(user_data['_id']),
            user_data['username'],
            user_data['email'],
            user_data['password'],
            user_data.get('dateJoined'),
            user_data.get('reputation', 0),
            user_data.get('status', 'active'),
            user_data.get('restrictionLevel', 0),
            user_data.get('badges', []),
            user_data.get('avatar'),
            user_data.get('community_interactions', {}),
            user_data.get('community_bans', {})
        )
    return None

# Define available badges with their criteria
BADGES = [
    {
        "name": "Community Member",
        "description": "Join a community",
        "type": "Bronze",
        "criteria": lambda user: len(user.community_interactions) >= 1
    },
    {
        "name": "Asker",
        "description": "Ask your first question in any community",
        "type": "Bronze",
        "criteria": lambda user: mongo.db.questions.count_documents({"memberId": user.id}) >= 1
    },
    {
        "name": "Questioner",
        "description": "Ask 5 questions in the community",
        "type": "Silver",
        "criteria": lambda user: mongo.db.questions.count_documents({"memberId": user.id}) >= 5
    },
    {
        "name": "Top Contributor",
        "description": "Achieve a reputation of 100 or more",
        "type": "Gold",
        "criteria": lambda user: user.reputation >= 100
    }
]


@routes.route('/communities')
def get_communities():
    try:
        communities = mongo.db.communities.find()
        return jsonify([community for community in communities])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/')
def home():
    print("home route called")
    return 'Welcome to Asksphere!'

@app.route('/register', methods=['POST'])
def register():
    print("register route called")
    data = request.get_json()
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'message': f'Missing required field: {field}'}), 400

    if mongo.db.users.find_one({'username': data['username']}):
        return jsonify({'message': 'Username already exists'}), 400

    if mongo.db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already exists'}), 400

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = {
        "username": data['username'],
        "email": data['email'],
        "password": hashed_password,
        "dateJoined": datetime.utcnow(),
        "reputation": 0,
        "status": "active",
        "restrictionLevel": 0,
        "badges": [],
        "avatar": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        "community_interactions": {},
        "community_bans": {}
    }
    result = mongo.db.users.insert_one(user)
    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': str(result.inserted_id),
            'username': data['username']
        }
    }), 201

@app.route('/login', methods=['POST'])
def login():
    print("login route called")
    data = request.get_json()
    required_fields = ['username', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'message': f'Missing required field: {field}'}), 400

    user_data = mongo.db.users.find_one({'username': data['username']})
    if user_data and bcrypt.check_password_hash(user_data['password'], data['password']):
        user = Member(
            str(user_data['_id']),
            user_data['username'],
            user_data['email'],
            user_data['password'],
            user_data.get('dateJoined'),
            user_data.get('reputation', 0),
            user_data.get('status', 'active'),
            user_data.get('restrictionLevel', 0),
            user_data.get('badges', []),
            user_data.get('avatar'),
            user_data.get('community_interactions', {}),
            user_data.get('community_bans', {})
        )
        login_user(user)
        return jsonify({
            'message': 'Logged in successfully',
            'user': {
                'id': str(user_data['_id']),
                'username': user_data['username'],
                'avatar': user_data.get('avatar')
            }
        }), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    print("logout route called")
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/protected', methods=['GET'])
@login_required
def protected():
    print("protected route called")
    return jsonify({'message': 'This is a protected route', 'user': current_user.username})

@app.route('/api/users/me', methods=['GET'])
@login_required
def get_current_user():
    print("get_current_user route called")
    user = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
    if not user:
        return jsonify({'message': 'User not found'}), 404

    return jsonify({
        "_id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "avatar": user.get("avatar"),
        "dateJoined": user.get("dateJoined").isoformat(),
        "reputation": user.get("reputation", 0),
        "status": user.get("status", "active"),
        "restrictionLevel": user.get("restrictionLevel", 0)
    }), 200

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    print("get_user route called")
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'User not found'}), 404
        return jsonify({
            'username': user['username'],
            'avatar': user.get('avatar')
        }), 200
    except Exception as e:
        return jsonify({'message': 'Invalid user ID', 'error': str(e)}), 400

@app.route('/api/users/avatar', methods=['POST'])
@login_required
def update_avatar():
    print("update_avatar route called")
    try:
        if 'avatar' not in request.files:
            return jsonify({'message': 'No avatar file provided'}), 400

        avatar_file = request.files['avatar']
        if avatar_file.filename == '':
            return jsonify({'message': 'No file selected'}), 400

        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' not in avatar_file.filename or avatar_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'message': 'Invalid file type. Allowed types: png, jpg, jpeg, gif'}), 400

        avatar_file.seek(0, 2)
        file_size = avatar_file.tell()
        if file_size > 2 * 1024 * 1024:
            return jsonify({'message': 'File size exceeds 2MB limit'}), 400
        avatar_file.seek(0)

        avatar_data = avatar_file.read()
        avatar_base64 = f"data:{avatar_file.content_type};base64,{base64.b64encode(avatar_data).decode('utf-8')}"

        mongo.db.users.update_one(
            {"_id": ObjectId(current_user.get_id())},
            {"$set": {"avatar": avatar_base64}}
        )
        current_user.avatar = avatar_base64
        return jsonify({'message': 'Avatar updated successfully', 'avatar': avatar_base64}), 200
    except Exception as e:
        return jsonify({'message': 'Error updating avatar', 'error': str(e)}), 500

@app.route('/communities', methods=['GET'])
def get_communities():
    print("get_communities route called")
    communities = mongo.db.communities.find()
    return jsonify([{
        "idCommunity": c["_id"],
        "name": c["name"],
        "description": c["description"]
    } for c in communities]), 200

@app.route('/communities/join', methods=['POST'])
@login_required
def join_community():
    print("join_community route called")
    data = request.get_json()
    community_id = int(data['communityId'])
    member_id = ObjectId(current_user.get_id())

    community = mongo.db.communities.find_one({"_id": community_id})
    if not community:
        return jsonify({'message': 'Community not found'}), 404

    if mongo.db.member_communities.find_one({"memberId": member_id, "communityId": community_id}):
        return jsonify({'message': 'Already a member of this community'}), 400

    member_community = Member_Community(member_id, community_id, datetime.utcnow())
    member_community.joinCommunity(member_id, community_id, mongo.db)

    badge_prefix = current_user.getBadgePrefix(community["name"])
    current_user.awardBadge(badge_prefix, mongo.db)

    return jsonify({'message': 'Joined community successfully'}), 200

@app.route('/communities/leave', methods=['POST'])
@login_required
def leave_community():
    print("leave_community route called")
    data = request.get_json()
    community_id = int(data['communityId'])
    member_id = ObjectId(current_user.get_id())

    if not mongo.db.member_communities.find_one({"memberId": member_id, "communityId": community_id}):
        return jsonify({'message': 'Not a member of this community'}), 400

    member_community = Member_Community(member_id, community_id, None)
    member_community.leaveCommunity(member_id, community_id, mongo.db)
    return jsonify({'message': 'Left community successfully'}), 200

@app.route('/member_communities', methods=['GET'])
@login_required
def get_member_communities():
    print("get_member_communities route called")
    member_communities = mongo.db.member_communities.find({"memberId": ObjectId(current_user.get_id())})
    response = [{"communityId": mc["communityId"]} for mc in member_communities]
    return jsonify(response), 200

@app.route('/validate-content', methods=['POST'])
@login_required
def validate_content():
    print("validate_content route called")
    data = request.get_json()
    content = data.get('content')
    community_id = int(data.get('communityId'))

    if not content or not community_id:
        return jsonify({'message': 'Missing content or communityId'}), 400

    validation_result = community_validator.validate_content(content, community_id)
    if validation_result is None:
        return jsonify({'message': 'Community not found'}), 404

    return jsonify({
        'is_relevant': validation_result['is_relevant'],
        'similarity_score': validation_result['similarity_score'],
        'suggested_community': validation_result['suggested_community'],
        'similar_questions': validation_result['similar_questions']
    }), 200

@app.route('/questions', methods=['POST'])
@login_required
def post_question():
    print("post_question route called")
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'Request body must be JSON'}), 400

        title = data.get('title')
        content = data.get('content')
        community_id = data.get('communityId')
        tags = data.get('tags', [])

        if not title or not content or community_id is None:
            return jsonify({'message': 'Title, content, and communityId are required'}), 400

        try:
            community_id = int(community_id)
        except (ValueError, TypeError) as e:
            return jsonify({'message': 'communityId must be a valid integer', 'error': str(e)}), 400

        member_community = mongo.db.member_communities.find_one({
            "memberId": ObjectId(current_user.id),
            "communityId": community_id
        })
        if not member_community:
            return jsonify({'message': 'Must be a member of the community to ask a question'}), 403

        print(f"Checking for ban in community ID: {community_id}")
        ban = mongo.db.community_bans.find_one({
            "memberId": ObjectId(current_user.id),
            "communityId": community_id
        })
        if ban and ban['expiresAt'] > datetime.utcnow():
            print(f"User is banned until {ban['expiresAt']}")
            return jsonify({
                'message': f"User is banned from this community until {ban['expiresAt'].isoformat()}"
            }), 403

        print(f"Validating content relevance for community ID: {community_id}")
        validation_result = community_validator.validate_content(content, community_id)
        if validation_result is None:
            print("Community not found")
            return jsonify({'message': 'Community not found'}), 404

        if not validation_result['is_relevant']:
            suggested_community = validation_result['suggested_community']
            print(f"Content not relevant. Suggested community: {suggested_community}")
            return jsonify({
                'message': 'Content is not relevant to this community',
                'suggested_community': suggested_community
            }), 400

        print("Checking for inappropriate content")
        filtered_content, warning = ai_filter.filterContent(
            content=content,
            memberId=ObjectId(current_user.id),
            questionId=None,
            answerId=None,
            communityId=community_id,
            db=mongo.db
        )
        if warning:
            print(f"Inappropriate content detected: {warning}")
            # Update inappropriate_content collection
            mongo.db.inappropriate_content.insert_one({
                "content": content,
                "memberId": ObjectId(current_user.id),
                "communityId": community_id,
                "questionId": None,
                "answerId": None,
                "timestamp": datetime.utcnow(),
                "keys": ["toxicity"],
                "isProcessed": False
            })
            # Increment restrictionLevel
            user = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
            restriction_level = (user.get('restrictionLevel', 0) or 0) + 1
            mongo.db.users.update_one(
                {"_id": ObjectId(current_user.id)},
                {"$set": {"restrictionLevel": restriction_level}}
            )
            # Create notification
            attempts_left = 5 - restriction_level
            feedback = f"You have {attempts_left} attempts left before a ban in community {community_id}."
            if attempts_left <= 2 and attempts_left > 0:
                feedback = f"Warning: You will be banned from this community if you reach 5 inappropriate attempts ({attempts_left} attempts left)."
            elif attempts_left <= 0:
                ban_duration_days = 1
                ban_expires = datetime.utcnow() + timedelta(days=ban_duration_days)
                mongo.db.community_bans.insert_one({
                    "memberId": ObjectId(current_user.id),
                    "communityId": community_id,
                    "startDate": datetime.utcnow(),
                    "expiresAt": ban_expires,
                    "reason": "Exceeded inappropriate content attempts"
                })
                # Clear inappropriate_content for this user and community
                mongo.db.inappropriate_content.delete_many({
                    "memberId": ObjectId(current_user.id),
                    "communityId": community_id
                })
                feedback = f"You have been banned from this community for {ban_duration_days} day(s). Ban expires on {ban_expires.isoformat()}."
                mongo.db.users.update_one(
                    {"_id": ObjectId(current_user.id)},
                    {"$set": {"restrictionLevel": 0}}
                )

            mongo.db.notifications.insert_one({
                "memberId": ObjectId(current_user.id),
                "type": "inappropriate",
                "message": feedback,
                "isRead": False,
                "createdAt": datetime.utcnow(),
                "communityId": community_id
            })
            return jsonify({
                'message': 'Content flagged as inappropriate',
                'feedback': feedback
            }), 400

        question = {
            "title": title,
            "content": filtered_content,
            "communityId": community_id,
            "memberId": ObjectId(current_user.id),
            "tags": tags,
            "dateCreated": datetime.utcnow(),
            "score": 0,
            "views": 0,
            "answers": 0
        }
        result = mongo.db.questions.insert_one(question)
        return jsonify({
            'message': 'Question posted successfully',
            'questionId': str(result.inserted_id)
        }), 201

    except Exception as e:
        print(f"Error posting question: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Error posting question', 'error': str(e)}), 500

@app.route('/questions', methods=['GET'])
def get_questions():
    print("get_questions route called")
    questions = mongo.db.questions.find()
    response = []
    for question in questions:
        answers_count = mongo.db.answers.count_documents({"questionId": question["_id"]})
        response.append({
            "_id": str(question["_id"]),
            "title": question["title"],
            "content": question["content"],
            "dateCreated": question["dateCreated"].isoformat(),
            "communityId": question["communityId"],
            "memberId": str(question["memberId"]),
            "score": question.get("score", 0),
            "views": question.get("views", 0),
            "answers": answers_count
        })
    return jsonify(response), 200

@app.route('/questions/<question_id>/answers', methods=['POST'])
@login_required
def answer_question(question_id):
    print("answer_question route called")
    if current_user.status == "banned":
        return jsonify({'message': 'User is banned'}), 403

    data = request.get_json()
    content = data['content']

    question = mongo.db.questions.find_one({"_id": ObjectId(question_id)})
    if not question:
        return jsonify({'message': 'Question not found'}), 404

    community_id = question["communityId"]
    ban_info = current_user.community_bans.get(str(community_id), {})
    if isinstance(ban_info, dict) and ban_info.get('status') == "banned":
        expiration = ban_info.get('expiration')
        if expiration and datetime.utcnow() < expiration:
            return jsonify({'message': f'User is banned from this community until {expiration}'}), 403

    if not mongo.db.member_communities.find_one({"memberId": ObjectId(current_user.get_id()), "communityId": community_id}):
        return jsonify({'message': 'Must be a member of the community to answer'}), 403

    filtered_content, feedback_message = ai_filter.filterContent(content, ObjectId(current_user.get_id()), ObjectId(question_id), None, community_id, mongo.db)
    if "inappropriate" in filtered_content.lower():
        return jsonify({'message': 'Content flagged as inappropriate', 'feedback': feedback_message}), 400

    validation_result = community_validator.validate_content(content, community_id)
    if validation_result is None:
        return jsonify({'message': 'Community not found'}), 404

    print(f"Validation Result for Community {community_id}: {validation_result}")

    if not validation_result['is_relevant']:
        return jsonify({
            'message': 'Content is not relevant to this community',
            'suggested_community': validation_result['suggested_community']
        }), 400

    answer = current_user.answerQuestion(content, ObjectId(question_id))
    result = mongo.db.answers.insert_one({
        "content": answer.content,
        "dateCreated": answer.dateCreated,
        "memberId": answer.memberId,
        "questionId": answer.questionId,
        "score": answer.score
    })

    # Update the question's answers count
    mongo.db.questions.update_one(
        {"_id": ObjectId(question_id)},
        {"$inc": {"answers": 1}}
    )

    # Notify the question owner (if the answerer is not the question owner)
    question_owner_id = question["memberId"]
    if str(question_owner_id) != current_user.id:
        question_owner = mongo.db.users.find_one({"_id": question_owner_id})
        if question_owner:
            question_owner_obj = Member(
                str(question_owner['_id']),
                question_owner['username'],
                question_owner['email'],
                question_owner['password'],
                question_owner.get('dateJoined'),
                question_owner.get('reputation', 0),
                question_owner.get('status', 'active'),
                question_owner.get('restrictionLevel', 0),
                question_owner.get('badges', []),
                question_owner.get('avatar'),
                question_owner.get('community_interactions', {}),
                question_owner.get('community_bans', {})
            )
            question_owner_obj.createNotification(
                message=f"{current_user.username} answered your question: {question['title']}",
                type="answer",
                relatedId=str(result.inserted_id),
                db=mongo.db
            )

    current_user.trackInteraction(community_id, "answers", mongo.db)

    return jsonify({'message': 'Answer posted successfully', 'id': str(result.inserted_id)}), 201

@app.route('/questions/<question_id>/answers', methods=['GET'])
def get_answers(question_id):
    print("get_answers route called")
    try:
        answers = mongo.db.answers.find({"questionId": ObjectId(question_id)})
        answers_list = []
        for answer in answers:
            answers_list.append({
                "_id": str(answer["_id"]),
                "content": answer["content"],
                "dateCreated": answer["dateCreated"].isoformat(),
                "memberId": str(answer["memberId"]),
                "questionId": str(answer["questionId"]),
                "score": answer.get("score", 0)
            })
        return jsonify(answers_list), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching answers', 'error': str(e)}), 500

@app.route('/vote', methods=['POST'])
@login_required
def vote():
    try:
        data = request.get_json()
        question_id = data.get('questionId')
        answer_id = data.get('answerId')
        value = data.get('value')

        if value not in [1, -1]:
            return jsonify({'message': 'Invalid vote value'}), 400

        if question_id:
            question = mongo.db.questions.find_one({"_id": ObjectId(question_id)})
            if not question:
                return jsonify({'message': 'Question not found'}), 404

            existing_vote = mongo.db.votes.find_one({
                "memberId": ObjectId(current_user.id),
                "questionId": ObjectId(question_id)
            })

            # Notify the question owner (if the voter is not the question owner)
            question_owner_id = question["memberId"]
            if str(question_owner_id) != current_user.id:
                question_owner = mongo.db.users.find_one({"_id": question_owner_id})
                if question_owner:
                    question_owner_obj = Member(
                        str(question_owner['_id']),
                        question_owner['username'],
                        question_owner['email'],
                        question_owner['password'],
                        question_owner.get('dateJoined'),
                        question_owner.get('reputation', 0),
                        question_owner.get('status', 'active'),
                        question_owner.get('restrictionLevel', 0),
                        question_owner.get('badges', []),
                        question_owner.get('avatar'),
                        question_owner.get('community_interactions', {}),
                        question_owner.get('community_bans', {})
                    )
                    vote_action = "upvoted" if value == 1 else "downvoted"
                    if not existing_vote:  # New vote
                        question_owner_obj.createNotification(
                            message=f"{current_user.username} {vote_action} your question: {question['title']}",
                            type="vote",
                            relatedId=str(question_id),
                            db=mongo.db
                        )
                    elif existing_vote['value'] != value:  # Vote changed
                        question_owner_obj.createNotification(
                            message=f"{current_user.username} changed their vote to {vote_action} on your question: {question['title']}",
                            type="vote",
                            relatedId=str(question_id),
                            db=mongo.db
                        )

            if existing_vote:
                if existing_vote['value'] == value:
                    mongo.db.votes.delete_one({
                        "memberId": ObjectId(current_user.id),
                        "questionId": ObjectId(question_id)
                    })
                    mongo.db.questions.update_one(
                        {"_id": ObjectId(question_id)},
                        {"$inc": {"score": -value}}
                    )
                    return jsonify({'message': 'Vote removed', 'newVote': 0}), 200
                else:
                    mongo.db.votes.update_one(
                        {"memberId": ObjectId(current_user.id), "questionId": ObjectId(question_id)},
                        {"$set": {"value": value}}
                    )
                    old_value = existing_vote['value']
                    score_change = -old_value + value
                    mongo.db.questions.update_one(
                        {"_id": ObjectId(question_id)},
                        {"$inc": {"score": score_change}}
                    )
                    return jsonify({'message': 'Vote updated', 'newVote': value}), 200
            else:
                mongo.db.votes.insert_one({
                    "memberId": ObjectId(current_user.id),
                    "questionId": ObjectId(question_id),
                    "value": value,
                    "date": datetime.utcnow()
                })
                mongo.db.questions.update_one(
                    {"_id": ObjectId(question_id)},
                    {"$inc": {"score": value}}
                )
                return jsonify({'message': 'Vote recorded', 'newVote': value}), 200

        elif answer_id:
            answer = mongo.db.answers.find_one({"_id": ObjectId(answer_id)})
            if not answer:
                return jsonify({'message': 'Answer not found'}), 404

            existing_vote = mongo.db.votes.find_one({
                "memberId": ObjectId(current_user.id),
                "answerId": ObjectId(answer_id)
            })

            # Notify the answer owner (if the voter is not the answer owner)
            answer_owner_id = answer["memberId"]
            if str(answer_owner_id) != current_user.id:
                answer_owner = mongo.db.users.find_one({"_id": answer_owner_id})
                if answer_owner:
                    answer_owner_obj = Member(
                        str(answer_owner['_id']),
                        answer_owner['username'],
                        answer_owner['email'],
                        answer_owner['password'],
                        answer_owner.get('dateJoined'),
                        answer_owner.get('reputation', 0),
                        question_owner.get('status', 'active'),
                        question_owner.get('restrictionLevel', 0),
                        question_owner.get('badges', []),
                        question_owner.get('avatar'),
                        question_owner.get('community_interactions', {}),
                        question_owner.get('community_bans', {})
                    )
                    vote_action = "upvoted" if value == 1 else "downvoted"
                    if not existing_vote:  # New vote
                        answer_owner_obj.createNotification(
                            message=f"{current_user.username} {vote_action} your answer",
                            type="vote",
                            relatedId=str(answer_id),
                            db=mongo.db
                        )
                    elif existing_vote['value'] != value:  # Vote changed
                        answer_owner_obj.createNotification(
                            message=f"{current_user.username} changed their vote to {vote_action} on your answer",
                            type="vote",
                            relatedId=str(answer_id),
                            db=mongo.db
                        )

            if existing_vote:
                if existing_vote['value'] == value:
                    mongo.db.votes.delete_one({
                        "memberId": ObjectId(current_user.id),
                        "answerId": ObjectId(answer_id)
                    })
                    mongo.db.answers.update_one(
                        {"_id": ObjectId(answer_id)},
                        {"$inc": {"score": -value}}
                    )
                    return jsonify({'message': 'Vote removed', 'newVote': 0}), 200
                else:
                    mongo.db.votes.update_one(
                        {"memberId": ObjectId(current_user.id), "answerId": ObjectId(answer_id)},
                        {"$set": {"value": value}}
                    )
                    old_value = existing_vote['value']
                    score_change = -old_value + value
                    mongo.db.answers.update_one(
                        {"_id": ObjectId(answer_id)},
                        {"$inc": {"score": score_change}}
                    )
                    return jsonify({'message': 'Vote updated', 'newVote': value}), 200
            else:
                mongo.db.votes.insert_one({
                    "memberId": ObjectId(current_user.id),
                    "answerId": ObjectId(answer_id),
                    "value": value,
                    "date": datetime.utcnow()
                })
                mongo.db.answers.update_one(
                    {"_id": ObjectId(answer_id)},
                    {"$inc": {"score": value}}
                )
                return jsonify({'message': 'Vote recorded', 'newVote': value}), 200

        else:
            return jsonify({'message': 'Must provide questionId or answerId'}), 400

    except Exception as e:
        return jsonify({'message': 'Error voting', 'error': str(e)}), 500

@app.route('/profile', methods=['PUT'])
@login_required
def edit_profile():
    print("edit_profile route called")
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')

    if not email:
        return jsonify({'message': 'Email is required'}), 400
    if not username:
        return jsonify({'message': 'Username is required'}), 400

    existing_user = mongo.db.users.find_one({"username": username})
    if existing_user and str(existing_user['_id']) != current_user.get_id():
        return jsonify({'message': 'Username already exists'}), 400

    current_user.editProfile(email, username)
    mongo.db.users.update_one(
        {"_id": ObjectId(current_user.get_id())},
        {"$set": {"email": email, "username": username}}
    )
    return jsonify({'message': 'Profile updated successfully', 'username': username}), 200

@app.route('/password', methods=['PUT'])
@login_required
def change_password():
    print("change_password route called")
    data = request.get_json()
    
    # Validate required fields
    if not data.get('password') or not data.get('confirm_password'):
        return jsonify({'message': 'New password and confirmation password are required'}), 400

    new_password = data['password']
    confirm_password = data['confirm_password']

    # Check if passwords match
    if new_password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400

    # Validate password requirements (e.g., minimum length)
    if len(new_password) < 8:
        return jsonify({'message': 'Password must be at least 8 characters long'}), 400

    # Hash the new password and update
    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    current_user.changePassword(hashed_password)
    mongo.db.users.update_one(
        {"_id": ObjectId(current_user.get_id())},
        {"$set": {"password": hashed_password}}
    )
    return jsonify({'message': 'Password changed successfully'}), 200

@app.route('/questions/<question_id>', methods=['GET'])
def get_question(question_id):
    print("get_question route called")
    try:
        question = mongo.db.questions.find_one({"_id": ObjectId(question_id)})
        if not question:
            return jsonify({'message': 'Question not found'}), 404

        return jsonify({
            "_id": str(question["_id"]),
            "title": question["title"],
            "content": question["content"],
            "dateCreated": question["dateCreated"].isoformat(),
            "communityId": question["communityId"],
            "memberId": str(question["memberId"]),
            "score": question.get("score", 0),
            "views": question.get("views", 0),
            "answers": question.get("answers", 0)
        }), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching question', 'error': str(e)}), 500

@app.route('/questions/<question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    print("delete_question route called")
    try:
        question = mongo.db.questions.find_one({"_id": ObjectId(question_id)})
        if not question:
            return jsonify({'message': 'Question not found'}), 404

        if str(question['memberId']) != current_user.id:
            return jsonify({'message': 'Unauthorized: You can only delete your own questions'}), 403

        # Delete answers associated with the question
        answers = mongo.db.answers.find({"questionId": ObjectId(question_id)})
        answer_ids = [answer["_id"] for answer in answers]

        # Delete notifications related to the question (type="vote" or type="answer")
        mongo.db.notifications.delete_many({
            "$or": [
                {"type": "vote", "relatedId": question_id},
                {"type": "answer", "relatedId": {"$in": [str(aid) for aid in answer_ids]}}
            ]
        })

        # Delete the answers, votes, and the question
        mongo.db.answers.delete_many({"questionId": ObjectId(question_id)})
        mongo.db.votes.delete_many({"questionId": ObjectId(question_id)})
        mongo.db.questions.delete_one({"_id": ObjectId(question_id)})

        return jsonify({'message': 'Question deleted successfully'}), 200
    except Exception as e:
        return jsonify({'message': 'Error deleting question', 'error': str(e)}), 500

@app.route('/answers/<answer_id>', methods=['DELETE'])
@login_required
def delete_answer(answer_id):
    print("delete_answer route called")
    try:
        answer = mongo.db.answers.find_one({"_id": ObjectId(answer_id)})
        if not answer:
            return jsonify({'message': 'Answer not found'}), 404

        if str(answer['memberId']) != current_user.id:
            return jsonify({'message': 'Unauthorized: You can only delete your own answers'}), 403

        # Delete notifications related to the answer (type="answer" or type="vote")
        mongo.db.notifications.delete_many({
            "$or": [
                {"type": "answer", "relatedId": answer_id},
                {"type": "vote", "relatedId": answer_id}
            ]
        })

        # Delete the answer and update the question's answer count
        mongo.db.answers.delete_one({"_id": ObjectId(answer_id)})
        mongo.db.questions.update_one(
            {"_id": answer['questionId']},
            {"$inc": {"answers": -1}}
        )

        return jsonify({'message': 'Answer deleted successfully'}), 200
    except Exception as e:
        return jsonify({'message': 'Error deleting answer', 'error': str(e)}), 500

@app.route('/answers/<answer_id>', methods=['PUT'])
@login_required
def update_answer(answer_id):
    print("update_answer route called")
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        content = data.get('content')
        if not content:
            print("Content is missing")
            return jsonify({'message': 'Content is required'}), 400

        print(f"Looking for answer with ID: {answer_id}")
        answer = mongo.db.answers.find_one({"_id": ObjectId(answer_id)})
        if not answer:
            print("Answer not found")
            return jsonify({'message': 'Answer not found'}), 404

        print(f"Answer memberId: {answer['memberId']}, Current user ID: {current_user.id}")
        if str(answer['memberId']) != current_user.id:
            print("Unauthorized: User does not own this answer")
            return jsonify({'message': 'Unauthorized: You can only update your own answers'}), 403

        print(f"Looking for question with ID: {answer['questionId']}")
        question = mongo.db.questions.find_one({"_id": answer['questionId']})
        if not question:
            print("Question not found")
            return jsonify({'message': 'Question not found'}), 404

        community_id = question['communityId']
        print(f"Checking for ban in community ID: {community_id}")
        ban = mongo.db.community_bans.find_one({
            "memberId": ObjectId(current_user.id),
            "communityId": community_id
        })
        if ban and ban['expiresAt'] > datetime.utcnow():
            print(f"User is banned until {ban['expiresAt']}")
            return jsonify({
                'message': f"User is banned from this community until {ban['expiresAt'].isoformat()}"
            }), 403

        print(f"Validating content relevance for community ID: {community_id}")
        validation_result = community_validator.validate_content(content, community_id)
        if validation_result is None:
            print("Community not found")
            return jsonify({'message': 'Community not found'}), 404

        if not validation_result['is_relevant']:
            suggested_community = validation_result['suggested_community']
            print(f"Content not relevant. Suggested community: {suggested_community}")
            return jsonify({
                'message': 'Content is not relevant to this community',
                'suggested_community': suggested_community
            }), 400

        print("Checking for inappropriate content")
        filtered_content, warning = ai_filter.filterContent(
            content=content,
            memberId=ObjectId(current_user.id),
            questionId=str(answer['questionId']),
            answerId=answer_id,
            communityId=community_id,
            db=mongo.db
        )
        if warning:
            print(f"Inappropriate content detected: {warning}")
            # Update inappropriate_content collection
            mongo.db.inappropriate_content.insert_one({
                "content": content,
                "memberId": ObjectId(current_user.id),
                "communityId": community_id,
                "questionId": str(answer['questionId']),
                "answerId": answer_id,
                "timestamp": datetime.utcnow(),
                "keys": ["toxicity"],  # Adjust based on AIContentFilter logic
                "isProcessed": False
            })
            # Increment restrictionLevel
            user = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
            restriction_level = (user.get('restrictionLevel', 0) or 0) + 1
            mongo.db.users.update_one(
                {"_id": ObjectId(current_user.id)},
                {"$set": {"restrictionLevel": restriction_level}}
            )
            # Create notification
            attempts_left = 5 - restriction_level
            feedback = f"You have {attempts_left} attempts left before a ban in community {community_id}."
            if attempts_left <= 2 and attempts_left > 0:
                feedback = f"Warning: You will be banned from this community if you reach 5 inappropriate attempts ({attempts_left} attempts left)."
            elif attempts_left <= 0:
                ban_duration_days = 1
                ban_expires = datetime.utcnow() + timedelta(days=ban_duration_days)
                mongo.db.community_bans.insert_one({
                    "memberId": ObjectId(current_user.id),
                    "communityId": community_id,
                    "startDate": datetime.utcnow(),
                    "expiresAt": ban_expires,
                    "reason": "Exceeded inappropriate content attempts"
                })
                # Clear inappropriate_content for this user and community
                mongo.db.inappropriate_content.delete_many({
                    "memberId": ObjectId(current_user.id),
                    "communityId": community_id
                })
                feedback = f"You have been banned from this community for {ban_duration_days} day(s). Ban expires on {ban_expires.isoformat()}."
                mongo.db.users.update_one(
                    {"_id": ObjectId(current_user.id)},
                    {"$set": {"restrictionLevel": 0}}
                )

            mongo.db.notifications.insert_one({
                "memberId": ObjectId(current_user.id),
                "type": "inappropriate",
                "message": feedback,
                "isRead": False,
                "createdAt": datetime.utcnow(),
                "communityId": community_id
            })
            return jsonify({
                'message': 'Content flagged as inappropriate',
                'feedback': feedback
            }), 400

        print("Updating answer in database")
        updated_answer = {
            "content": filtered_content,
            "dateUpdated": datetime.utcnow()
        }
        result = mongo.db.answers.update_one(
            {"_id": ObjectId(answer_id)},
            {"$set": updated_answer}
        )
        print(f"Update result: {result.modified_count} document(s) modified")

        updated_answer_doc = mongo.db.answers.find_one({"_id": ObjectId(answer_id)})
        return jsonify({
            'id': answer_id,
            'content': updated_answer_doc['content'],
            'dateUpdated': updated_answer_doc['dateUpdated'].isoformat()
        }), 200
    except Exception as e:
        print(f"Error in update_answer: {str(e)}")
        return jsonify({'message': 'Error updating answer', 'error': str(e)}), 500

@app.route('/user-votes', methods=['POST'])
@login_required
def get_user_votes():
    try:
        data = request.get_json()
        answer_ids = data.get('answerIds', [])
        user_id = data.get('userId')

        if not user_id or not answer_ids:
            return jsonify({'message': 'userId and answerIds are required'}), 400

        votes = mongo.db.votes.find({
            "memberId": ObjectId(user_id),
            "answerId": {"$in": [ObjectId(aid) for aid in answer_ids]}
        })

        vote_map = {}
        for vote in votes:
            vote_map[str(vote['answerId'])] = vote['value']

        for aid in answer_ids:
            if aid not in vote_map:
                vote_map[aid] = 0

        return jsonify(vote_map), 200

    except Exception as e:
        return jsonify({'message': 'Error fetching user votes', 'error': str(e)}), 500

@app.route('/badges', methods=['GET'])
@login_required
def get_badges():
    print("get_badges route called")
    # Check which badges the user has earned
    user_badges = current_user.badges
    earned_badges = []

    for badge in BADGES:
        if badge["criteria"](current_user) and badge["name"] not in user_badges:
            current_user.award_badge(badge["name"])
            mongo.db.users.update_one(
                {"_id": ObjectId(current_user.get_id())},
                {"$set": {"badges": current_user.badges}}
            )

    # Prepare the response with all badges and their earned status
    badges_with_status = []
    for badge in BADGES:
        badges_with_status.append({
            "name": badge["name"],
            "description": badge["description"],
            "type": badge["type"],
            "earned": badge["name"] in current_user.badges,
            "count": mongo.db.users.count_documents({"badges": badge["name"]})  # Number of users who have this badge
        })

    return jsonify({"badges": badges_with_status}), 200

@app.route('/score', methods=['GET'])
@login_required
def view_score():
    print("view_score route called")
    return jsonify({'score': current_user.viewScore()}), 200

@app.route('/recommended_questions', methods=['GET'])
@login_required
def get_recommended_questions():
    print("get_recommended_questions route called")
    member_communities = mongo.db.member_communities.find({"memberId": ObjectId(current_user.get_id())})
    community_ids = [mc["communityId"] for mc in member_communities]
    
    if not community_ids:
        return jsonify([]), 200

    questions = mongo.db.questions.find({
        "communityId": {"$in": community_ids}
    }).sort([
        ("score", -1),
        ("dateCreated", -1)
    ]).limit(5)

    response = []
    for question in questions:
        member = mongo.db.users.find_one({"_id": ObjectId(question["memberId"])})
        username = member["username"] if member else "Unknown"
        
        response.append({
            "_id": str(question["_id"]),
            "title": question["title"],
            "dateCreated": question["dateCreated"].isoformat(),
            "user": username
        })
    return jsonify(response), 200

@app.route('/questions/<question_id>/view', methods=['POST'])
def increment_question_views(question_id):
    print("increment_question_views route called")
    try:
        mongo.db.questions.update_one(
            {"_id": ObjectId(question_id)},
            {"$inc": {"views": 1}}
        )
        return jsonify({'message': 'View count incremented'}), 200
    except Exception as e:
        return jsonify({'message': 'Error incrementing views', 'error': str(e)}), 500

@app.route('/api/users/me/communities', methods=['GET'])
@login_required
def get_user_communities():
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
        if not user:
            return jsonify({'message': 'User not found'}), 404

        communities = user.get('communities', [])
        return jsonify(communities), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching communities', 'error': str(e)}), 500

@app.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    print("get_notifications route called")
    try:
        notifications = mongo.db.notifications.find({"memberId": ObjectId(current_user.id)}).sort("dateCreated", -1)
        response = []
        for notification in notifications:
            # Skip notifications if the related question or answer is deleted
            if notification["type"] in ["answer", "vote"]:
                if notification["relatedId"]:
                    if notification["type"] == "answer":
                        # Check if the answer exists
                        answer = mongo.db.answers.find_one({"_id": ObjectId(notification["relatedId"])})
                        if not answer:
                            continue  # Skip if answer is deleted
                        # Check if the question exists
                        question = mongo.db.questions.find_one({"_id": answer["questionId"]})
                        if not question:
                            continue  # Skip if question is deleted
                        notification_data = {
                            "_id": str(notification["_id"]),
                            "message": notification["message"],
                            "type": notification["type"],
                            "relatedId": str(notification["relatedId"]),
                            "read": notification["read"],
                            "dateCreated": notification.get("createdAt", notification.get("dateCreated")).isoformat(),
                            "questionId": str(answer["questionId"])
                        }
                    elif notification["type"] == "vote":
                        # For vote notifications, relatedId can be a questionId or answerId
                        related_id = notification["relatedId"]
                        question = mongo.db.questions.find_one({"_id": ObjectId(related_id)})
                        answer = mongo.db.answers.find_one({"_id": ObjectId(related_id)})
                        if not question and not answer:
                            continue  # Skip if neither question nor answer exists
                        question_id = related_id if question else str(answer["questionId"])
                        notification_data = {
                            "_id": str(notification["_id"]),
                            "message": notification["message"],
                            "type": notification["type"],
                            "relatedId": str(notification["relatedId"]),
                            "read": notification["read"],
                            "dateCreated": notification.get("createdAt", notification.get("dateCreated")).isoformat(),
                            "questionId": question_id
                        }
                else:
                    continue  # Skip if relatedId is missing
            else:
                # For other types (e.g., badge, ban, warning), no relatedId validation needed
                notification_data = {
                    "_id": str(notification["_id"]),
                    "message": notification["message"],
                    "type": notification["type"],
                    "relatedId": str(notification["relatedId"]) if notification["relatedId"] else None,
                    "read": notification["read"],
                    "dateCreated": notification.get("createdAt", notification.get("dateCreated")).isoformat()
                }
            response.append(notification_data)
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching notifications', 'error': str(e)}), 500

@app.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    print("mark_notifications_read route called")
    try:
        data = request.get_json()
        notification_ids = data.get('notificationIds', [])
        if not notification_ids:
            # Mark all notifications as read if no specific IDs are provided
            mongo.db.notifications.update_many(
                {"memberId": ObjectId(current_user.id), "read": False},
                {"$set": {"read": True}}
            )
            return jsonify({'message': 'All notifications marked as read'}), 200

        # Mark specific notifications as read
        mongo.db.notifications.update_many(
            {"_id": {"$in": [ObjectId(nid) for nid in notification_ids]}, "memberId": ObjectId(current_user.id)},
            {"$set": {"read": True}}
        )
        return jsonify({'message': 'Notifications marked as read'}), 200
    except Exception as e:
        return jsonify({'message': 'Error marking notifications as read', 'error': str(e)}), 500

# Add a route to fetch answer details (if needed)
@app.route('/answers/<answer_id>', methods=['GET'])
@login_required
def get_answer(answer_id):
    try:
        answer = mongo.db.answers.find_one({"_id": ObjectId(answer_id)})
        if not answer:
            return jsonify({'message': 'Answer not found'}), 404
        return jsonify({
            "_id": str(answer["_id"]),
            "questionId": str(answer["questionId"]),
            "content": answer["content"],
            "memberId": str(answer["memberId"]),
            "dateCreated": answer["dateCreated"].isoformat()
        }), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching answer', 'error': str(e)}), 500
    
@app.route('/api/users/<user_id>/profile', methods=['GET'])
@login_required
def get_user_profile(user_id):
    print("get_user_profile route called")
    try:
        # Fetch the user data
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Count the user's questions
        questions_count = mongo.db.questions.count_documents({"memberId": ObjectId(user_id)})

        # Count the user's answers
        answers_count = mongo.db.answers.count_documents({"memberId": ObjectId(user_id)})

        # Prepare the response
        profile_data = {
            "username": user["username"],
            "avatar": user.get("avatar"),
            "questionsCount": questions_count,
            "answersCount": answers_count,
            "status": user.get("status", "active"),
            "reputation": user.get("reputation", 0),
            "dateJoined": user.get("dateJoined").isoformat() if user.get("dateJoined") else None,
            "badges": user.get("badges", [])
        }
        return jsonify(profile_data), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching user profile', 'error': str(e)}), 400

@app.route('/api/users/me/stats', methods=['GET'])
@login_required
def get_user_stats():
    try:
        user_id = ObjectId(current_user.id)
        
        # Get current date and calculate time ranges
        now = datetime.utcnow()
        one_year_ago = now - timedelta(days=365)
        one_week_ago = now - timedelta(days=7)
        current_month = now.month - 1  # 0-based index
        prev_month = current_month - 1 if current_month > 0 else 11
        
        # Initialize monthly arrays with zeros
        monthly_questions = [0] * 12
        monthly_answers = [0] * 12
        monthly_votes = [0] * 12
        
        # Get monthly questions
        questions = mongo.db.questions.aggregate([
            {"$match": {
                "memberId": user_id,
                "dateCreated": {"$gte": one_year_ago}
            }},
            {"$group": {
                "_id": {"$month": "$dateCreated"},
                "count": {"$sum": 1}
            }}
        ])
        
        for q in questions:
            month_index = q['_id'] - 1
            if 0 <= month_index < 12:
                monthly_questions[month_index] = q['count']
        
        # Get monthly answers
        answers = mongo.db.answers.aggregate([
            {"$match": {
                "memberId": user_id,
                "dateCreated": {"$gte": one_year_ago}
            }},
            {"$group": {
                "_id": {"$month": "$dateCreated"},
                "count": {"$sum": 1}
            }}
        ])
        
        for a in answers:
            month_index = a['_id'] - 1
            if 0 <= month_index < 12:
                monthly_answers[month_index] = a['count']
        
        # Get monthly votes
        votes = mongo.db.votes.aggregate([
            {"$match": {
                "memberId": user_id,
                "date": {"$gte": one_year_ago}
            }},
            {"$group": {
                "_id": {"$month": "$date"},
                "count": {"$sum": 1}
            }}
        ])
        
        for v in votes:
            month_index = v['_id'] - 1
            if 0 <= month_index < 12:
                monthly_votes[month_index] = v['count']
        
        # Weekly activity (last 7 days)
        weekly_activity = [0] * 7  # Sunday to Saturday
        
        # Get daily activity counts (questions + answers)
        for i in range(7):
            day_start = now - timedelta(days=(6-i))
            day_end = day_start + timedelta(days=1)
            
            # Count questions
            weekly_activity[i] += mongo.db.questions.count_documents({
                "memberId": user_id,
                "dateCreated": {"$gte": day_start, "$lt": day_end}
            })
            
            # Count answers
            weekly_activity[i] += mongo.db.answers.count_documents({
                "memberId": user_id,
                "dateCreated": {"$gte": day_start, "$lt": day_end}
            })
        
        # Calculate trends
        def calculate_trend(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100)
        
        question_trend = calculate_trend(monthly_questions[current_month], monthly_questions[prev_month])
        answer_trend = calculate_trend(monthly_answers[current_month], monthly_answers[prev_month])
        vote_trend = calculate_trend(monthly_votes[current_month], monthly_votes[prev_month])
        
        # For views trend, we need to implement monthly views tracking
        view_trend = 0  # Placeholder - implement similar to others
        
        # Total counts
        total_questions = mongo.db.questions.count_documents({"memberId": user_id})
        total_answers = mongo.db.answers.count_documents({"memberId": user_id})
        total_votes = mongo.db.votes.count_documents({"memberId": user_id})
        
        # Total views (sum of all question views)
        total_views_result = mongo.db.questions.aggregate([
            {"$match": {"memberId": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$views"}}}
        ])
        
        total_views = next(total_views_result, {}).get('total', 0)
        
        return jsonify({
            "monthlyQuestions": monthly_questions,
            "monthlyAnswers": monthly_answers,
            "monthlyVotes": monthly_votes,
            "weeklyActivity": weekly_activity,
            "totalQuestions": total_questions,
            "totalAnswers": total_answers,
            "totalVotes": total_votes,
            "totalViews": total_views,
            "questionTrend": question_trend,
            "answerTrend": answer_trend,
            "voteTrend": vote_trend,
            "viewTrend": view_trend,
            "success": True
        }), 200
        
    except Exception as e:
        print(f"Error fetching user stats: {str(e)}")
        return jsonify({
            "message": "Error fetching user stats",
            "error": str(e),
            "success": False
        }), 500
    
@app.route('/api/communities/<int:community_id>/stats', methods=['GET'])
@login_required
def get_community_stats(community_id):
    try:
        # Get current date and calculate time ranges
        now = datetime.utcnow()
        one_year_ago = now - timedelta(days=365)
        one_week_ago = now - timedelta(days=7)
        current_month = now.month - 1  # 0-based index
        prev_month = current_month - 1 if current_month > 0 else 11
        
        # Initialize monthly arrays with zeros
        monthly_questions = [0] * 12
        monthly_answers = [0] * 12
        monthly_users = [0] * 12
        
        # Get monthly questions
        questions = mongo.db.questions.aggregate([
            {"$match": {
                "communityId": community_id,
                "dateCreated": {"$gte": one_year_ago}
            }},
            {"$group": {
                "_id": {"$month": "$dateCreated"},
                "count": {"$sum": 1}
            }}
        ])
        
        for q in questions:
            month_index = q['_id'] - 1
            if 0 <= month_index < 12:
                monthly_questions[month_index] = q['count']
        
        # Get monthly answers
        answers = mongo.db.answers.aggregate([
            {"$match": {
                "questionId": {"$in": [q["_id"] for q in mongo.db.questions.find({"communityId": community_id}, {"_id": 1})]},
                "dateCreated": {"$gte": one_year_ago}
            }},
            {"$group": {
                "_id": {"$month": "$dateCreated"},
                "count": {"$sum": 1}
            }}
        ])
        
        for a in answers:
            month_index = a['_id'] - 1
            if 0 <= month_index < 12:
                monthly_answers[month_index] = a['count']
        
        # Get monthly new users
        users = mongo.db.member_communities.aggregate([
            {"$match": {
                "communityId": community_id,
                "dateJoined": {"$gte": one_year_ago}
            }},
            {"$group": {
                "_id": {"$month": "$dateJoined"},
                "count": {"$sum": 1}
            }}
        ])
        
        for u in users:
            month_index = u['_id'] - 1
            if 0 <= month_index < 12:
                monthly_users[month_index] = u['count']
        
        # Weekly activity (last 7 days)
        weekly_activity = [0] * 7  # Sunday to Saturday
        
        # Get daily activity counts (questions + answers)
        for i in range(7):
            day_start = now - timedelta(days=(6-i))
            day_end = day_start + timedelta(days=1)
            
            # Count questions
            weekly_activity[i] += mongo.db.questions.count_documents({
                "communityId": community_id,
                "dateCreated": {"$gte": day_start, "$lt": day_end}
            })
            
            # Count answers
            weekly_activity[i] += mongo.db.answers.count_documents({
                "questionId": {"$in": [q["_id"] for q in mongo.db.questions.find({"communityId": community_id}, {"_id": 1})]},
                "dateCreated": {"$gte": day_start, "$lt": day_end}
            })
        
        # Calculate trends
        def calculate_trend(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100)
        
        question_trend = calculate_trend(monthly_questions[current_month], monthly_questions[prev_month])
        answer_trend = calculate_trend(monthly_answers[current_month], monthly_answers[prev_month])
        user_trend = calculate_trend(monthly_users[current_month], monthly_users[prev_month])
        
        # Total counts
        total_questions = mongo.db.questions.count_documents({"communityId": community_id})
        total_answers = mongo.db.answers.count_documents({
            "questionId": {"$in": [q["_id"] for q in mongo.db.questions.find({"communityId": community_id}, {"_id": 1})]}
        })
        
        # Active and banned users
        active_users = mongo.db.member_communities.count_documents({"communityId": community_id})
        banned_users = mongo.db.users.count_documents({
            f"community_bans.{community_id}.status": "banned"
        })
        
        return jsonify({
            "monthlyQuestions": monthly_questions,
            "monthlyAnswers": monthly_answers,
            "monthlyUsers": monthly_users,
            "weeklyActivity": weekly_activity,
            "totalQuestions": total_questions,
            "totalAnswers": total_answers,
            "activeUsers": active_users,
            "bannedUsers": banned_users,
            "questionTrend": question_trend,
            "answerTrend": answer_trend,
            "userTrend": user_trend,
            "success": True
        }), 200
        
    except Exception as e:
        print(f"Error fetching community stats: {str(e)}")
        return jsonify({
            "message": "Error fetching community stats",
            "error": str(e),
            "success": False
        }), 500

@app.route('/api/communities/<int:community_id>', methods=['GET'])
@login_required
def get_community(community_id):
    try:
        community = mongo.db.communities.find_one({"_id": community_id})
        if not community:
            return jsonify({'message': 'Community not found'}), 404
        return jsonify({
            "name": community["name"],
            "description": community["description"]
        }), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching community', 'error': str(e)}), 500
    
@app.route('/api/communities/<int:community_id>/members', methods=['GET'])
@login_required
def get_community_members(community_id):
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        active_members = list(mongo.db.member_communities.aggregate([
            {"$match": {"communityId": community_id}},
            {"$lookup": {
                "from": "users",
                "localField": "memberId",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$project": {
                "_id": "$user._id",
                "username": "$user.username",
                "avatar": "$user.avatar",
                "reputation": "$user.reputation",
                "dateJoined": {
                    "$cond": [
                        {"$eq": ["$dateJoined", None]},
                        {"$dateToString": {"format": "%Y-%m-%dT%H:%M:%S.%LZ", "date": "$$NOW"}},
                        {"$dateToString": {"format": "%Y-%m-%dT%H:%M:%S.%LZ", "date": "$dateJoined"}}
                    ]
                },
                "status": "$user.status"
            }},
            {"$match": {"status": "active"}},
            {"$skip": (page - 1) * per_page},
            {"$limit": per_page}
        ]))
        
        banned_members = list(mongo.db.users.aggregate([
            {"$match": {f"community_bans.{community_id}.status": "banned"}},
            {"$project": {
                "_id": 1,
                "username": 1,
                "avatar": 1,
                "reputation": 1,
                "status": 1,
                "dateJoined": {"$literal": None}
            }},
            {"$skip": (page - 1) * per_page},
            {"$limit": per_page}
        ]))
        
        total_active = mongo.db.member_communities.count_documents({"communityId": community_id})
        total_banned = mongo.db.users.count_documents({f"community_bans.{community_id}.status": "banned"})
        
        return jsonify({
            "activeMembers": active_members,
            "bannedMembers": banned_members,
            "totalActive": total_active,
            "totalBanned": total_banned,
            "success": True
        }), 200
        
    except Exception as e:
        print(f"Error fetching community members: {str(e)}")
        return jsonify({
            "message": "Error fetching community members",
            "error": str(e),
            "success": False
        }), 500
    
@app.route('/recover', methods=['POST'])
def initiate_password_recovery():
    """Step 1: Verify username and email"""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')

    if not username or not email:
        return jsonify({'message': 'Username and email are required'}), 400

    user = mongo.db.users.find_one({'username': username, 'email': email})
    if not user:
        return jsonify({'message': 'No account found with these credentials'}), 404

    # In a real app, you would generate a token and send an email here
    # For this simplified version, we'll just return success
    return jsonify({
        'message': 'Credentials verified. You can now reset your password.',
        'userId': str(user['_id'])
    }), 200

@app.route('/recover/reset', methods=['POST'])
def reset_password():
    """Step 2: Reset password after verification"""
    data = request.get_json()
    user_id = data.get('userId')
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')

    if not user_id or not new_password or not confirm_password:
        return jsonify({'message': 'All fields are required'}), 400

    if new_password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400

    if len(new_password) < 8:
        return jsonify({'message': 'Password must be at least 8 characters long'}), 400

    try:
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'User not found'}), 404

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'password': hashed_password}}
        )

        return jsonify({'message': 'Password updated successfully'}), 200
    except Exception as e:
        return jsonify({'message': 'Error resetting password', 'error': str(e)}), 500
    
@app.route('/api/validate-field', methods=['POST'])
def validate_field():
    print("validate_field route called")
    data = request.get_json()
    field = data.get('field')
    value = data.get('value')

    if not field or not value:
        return jsonify({'message': 'Field and value are required'}), 400

    if field not in ['username', 'email']:
        return jsonify({'message': 'Invalid field. Must be username or email'}), 400

    existing = mongo.db.users.find_one({field: value})
    if existing:
        return jsonify({
            'valid': False,
            'message': f'{field.capitalize()} already exists'
        }), 200

    return jsonify({'valid': True}), 200