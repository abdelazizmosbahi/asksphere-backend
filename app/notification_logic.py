def prioritize_notification(notification_type):
    priority_map = {
        'ban': 'high',
        'answer': 'high',
        'badge_awarded': 'medium',
        'vote': 'low',
        'restriction_warning': 'medium',
        'chatbot_response': 'medium'
    }
    return priority_map.get(notification_type, 'medium')