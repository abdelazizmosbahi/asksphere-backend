from app import app, mongo

# Populate the database with initial communities
with app.app_context():
    # Clear existing communities
    mongo.db.communities.drop()

    # Insert 6 communities
    communities = [
  { "_id": 1, "name": "Development", "description": "A community for developers to discuss programming languages, software development, coding tips, frameworks, tools, projects, and career advice" },
  { "_id": 2, "name": "Gaming", "description": "A community for gamers to discuss video games, gaming consoles, PC gaming, esports, strategies, tips, tricks, and experiences" },
  { "_id": 3, "name": "Music", "description": "A community for music lovers to discuss songs, artists, genres, music production, instruments, concerts, and music history" },
  { "_id": 4, "name": "Science", "description": "A community for discussing scientific discoveries, research, theories, experiments, physics, chemistry, biology, astronomy, and technology" },
  { "_id": 5, "name": "Art", "description": "A community for artists to share their work, techniques, styles, digital art, traditional art, photography, design, and creative inspiration" },
  { "_id": 6, "name": "Sports", "description": "A community for sports enthusiasts to discuss games, events, teams, athletes, fitness, training, sports strategies, and fan experiences" }
]
    mongo.db.communities.insert_many(communities)
    print("Inserted 6 communities into the database.")

if __name__ == '__main__':
    app.run(debug=True)