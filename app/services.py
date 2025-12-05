# Import regex for flexible query matching
from datetime import datetime
import re
import logging
from bson import ObjectId
from sentence_transformers import SentenceTransformer, util
from app.models import log_chat_interaction, get_questions_and_communities

# Configure logging for debugging
logger = logging.getLogger(__name__)

# Initialize SentenceTransformer model for question recommendation
model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to handle user queries for the User Support Chatbot
def handle_chat_query(mongo, user_id, query):
    # Process user query for the User Support Chatbot (rule-based placeholder)
    query = query.lower().strip()
    
    # Log the query for debugging
    logger.debug(f"Processing chatbot query: '{query}'")
    
    # Define rule-based responses with flexible regex patterns for each category
    # Category 1: Joining a Community
    if re.search(r'\b(join|member|become)\b.*\b(community|communities)\b', query):
        response = "To join a community, navigate to the Communities section in AskSphere, select a community like 'Development' or 'Gaming', and click 'Join'. Ensure you have an active account."
        logger.debug("Matched 'join community' pattern")
    
    # Category 2: Password Reset or Recovery
    elif re.search(r'\b(password|login)\b.*\b(forgot|reset|recover|change)\b', query):
        response = "To reset your password, go to the login page, click 'Forgot Password', and follow the instructions to receive a reset link via email."
        logger.debug("Matched 'password reset' pattern")
    
    # Category 3: Asking a Question
    elif re.search(r'\b(ask|post|submit)\b.*\b(question|questions)\b', query):
        response = "To ask a question, go to the desired community, click 'Post Question', and enter your question details. Ensure it complies with community guidelines."
        logger.debug("Matched 'ask question' pattern")
    
    # Category 4: Creating or Signing Up for an Account
    elif re.search(r'\b(create|sign\s*up|register|signup)\b.*\b(account|profile)\b', query):
        response = "To create an account, go to the AskSphere homepage, click 'Sign Up', and fill in your details (email, username, password). Verify your email to activate your account."
        logger.debug("Matched 'create account' pattern")
    
    # Category 5: Editing a Question, Answer, or Post
    elif re.search(r'\b(edit|update|change|modify)\b.*\b(question|answer|post)\b', query):
        response = "To edit a question or answer, go to your post in the community, click the 'Edit' button, make changes, and save. Note that edits must comply with community guidelines."
        logger.debug("Matched 'edit post' pattern")
    
    # Category 6: Deleting a Question, Answer, or Post
    elif re.search(r'\b(delete|remove)\b.*\b(question|answer|post)\b', query):
        response = "To delete your question or answer, go to the post, click the 'Delete' option, and confirm. Deleted posts cannot be recovered, so proceed carefully."
        logger.debug("Matched 'delete post' pattern")
    
    # Category 7: Viewing Notifications
    elif re.search(r'\b(view|check|see|look\s+at)\b.*\b(notification|notifications|alerts)\b', query):
        response = "To view notifications, go to your profile and click the 'Notifications' tab. You’ll see updates like responses to your questions, votes, or moderation alerts."
        logger.debug("Matched 'view notifications' pattern")
    
    # Category 8: Reporting Content or Users
    elif re.search(r'\b(report|flag)\b.*\b(content|user|post|question|answer)\b', query):
        response = "To report inappropriate content or a user, click the 'Report' button next to the post or user profile. Provide details, and our moderation team will review it."
        logger.debug("Matched 'report content' pattern")
    
    # Category 9: Account Bans or Restrictions
    elif re.search(r'\b(ban|banned|restrict|restricted|suspend|suspension|appeal)\b.*\b(account|profile)\b', query):
        response = "If your account is banned or restricted, you’ll receive a notification with details. Check the 'Notifications' tab or contact support for more information."
        logger.debug("Matched 'account ban/restriction' pattern")
    
    # Category 10: Searching for Communities or Questions
    elif re.search(r'\b(search|find|look\s+for)\b.*\b(community|communities|question|questions)\b', query):
        response = "To search for communities or questions, use the search bar at the top of the AskSphere page. Enter keywords to find relevant communities or posts."
        logger.debug("Matched 'search community/question' pattern")
    
    # Fallback for unmatched queries
    else:
        response = "Sorry, I didn't understand your request. Please try rephrasing or contact support for assistance."
        logger.debug("No pattern matched for query")
    
    # Log the interaction in MongoDB
    log_chat_interaction(mongo, user_id, query, response)
    return response
def log_chat_interaction(mongo, user_id, query, response):
    """
    Log chatbot interaction to MongoDB.
    
    Args:
        mongo: MongoDB client (mongo.db)
        user_id: String ID of the user
        query: User query string
        response: Chatbot response string
    """
    mongo.db.chat_interactions.insert_one({
        'userId': ObjectId(user_id),
        'query': query,
        'response': response,
        'timestamp': datetime.utcnow()
    })

# Function to recommend questions based on query similarity
def recommend_questions(mongo, query, community_id=None, top_k=5, similarity_threshold=0.0):
    # Recommend questions based on query similarity, optionally filtered by community_id
    logger.debug(f"Processing query: {query}, community_id: {community_id}")
    
    # Retrieve questions and communities
    questions, communities = get_questions_and_communities(mongo)
    
    # Log raw retrieved data
    logger.debug(f"Retrieved {len(questions)} questions: {[str(q) for q in questions]}")
    logger.debug(f"Retrieved {len(communities)} communities: {[str(c) for c in communities]}")
    
    # If community_id is provided, validate community existence
    if community_id:
        community = next((c for c in communities if str(c['_id']) == str(community_id)), None)
        if not community:
            logger.debug(f"Community ID {community_id} not found")
            return [], "Community not found"
        
        # Compute similarity between query and community (for debugging, not filtering)
        community_text = (community.get('name', '') + ' ' + community.get('description', ''))[:200]
        query_embedding = model.encode(query, convert_to_tensor=True)
        community_embedding = model.encode(community_text, convert_to_tensor=True)
        community_similarity = util.cos_sim(query_embedding, community_embedding)[0]
        logger.debug(f"Query similarity to community {community_id} ({community.get('name')}): {community_similarity}")
    
    # Filter questions by community_id if provided
    items = []
    for q in questions:
        if community_id is None or q.get('community') == next(c.get('name') for c in communities if str(c['_id']) == str(community_id)):
            text = (q.get('title', '') + ' ' + q.get('body', ''))[:200]
            items.append({
                'type': 'question',
                'id': str(q['_id']),
                'text': text,
                'community': q.get('community', '')
            })
    
    # Log items to be processed
    logger.debug(f"Processing {len(items)} questions: {[item['id'] for item in items]}")
    
    # Encode query
    query_embedding = model.encode(query, convert_to_tensor=True)
    
    # Process questions if available
    recommendations = []
    if items:
        item_texts = [item['text'] for item in items]
        item_embeddings = model.encode(item_texts, convert_to_tensor=True)
        
        # Compute cosine similarities for questions
        similarities = util.cos_sim(query_embedding, item_embeddings)[0]
        
        # Log similarity scores
        for idx, item in enumerate(items):
            logger.debug(f"Question ID: {item['id']}, Text: {item['text']}, Similarity: {similarities[idx]}")
        
        # Get top_k questions with similarity above threshold
        for idx in similarities.argsort(descending=True)[:top_k]:
            if similarities[idx] >= similarity_threshold:
                item = items[idx]
                recommendations.append({
                    'type': item['type'],
                    'id': item['id'],
                    'text': item['text'],
                    'community': item['community'],
                    'similarity': float(similarities[idx])
                })
    
    # Fallback to communities only if no questions meet the threshold and no community_id is specified
    if len(recommendations) < top_k and community_id is None and communities:
        community_items = []
        for c in communities:
            text = (c.get('name', '') + ' ' + c.get('description', ''))[:200]
            community_items.append({
                'type': 'community',
                'id': str(c['_id']),
                'text': text,
                'community': c.get('name', '')
            })
        
        if community_items:
            community_texts = [item['text'] for item in community_items]
            community_embeddings = model.encode(community_texts, convert_to_tensor=True)
            community_similarities = util.cos_sim(query_embedding, community_embeddings)[0]
            
            # Log community similarity scores
            for idx, item in enumerate(community_items):
                logger.debug(f"Community ID: {item['id']}, Text: {item['text']}, Similarity: {community_similarities[idx]}")
            
            # Add communities to fill up to top_k
            for idx in community_similarities.argsort(descending=True):
                if len(recommendations) < top_k and community_similarities[idx] >= similarity_threshold:
                    item = community_items[idx]
                    recommendations.append({
                        'type': item['type'],
                        'id': item['id'],
                        'text': item['text'],
                        'community': item['community'],
                        'similarity': float(community_similarities[idx])
                    })
    
    # Return empty list if no items meet the threshold
    if not recommendations:
        logger.debug("No recommendations found above similarity threshold")
        return [], "No relevant questions or communities found. Try a more specific query."
    
    return recommendations, None