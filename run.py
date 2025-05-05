from app import app, mongo

# Populate the database with initial communities
with app.app_context():
    # Clear existing communities
    mongo.db.communities.drop()

    # Insert 6 communities with concise, independent descriptions
    communities = [
        {
            "_id": 1,
            "name": "Development",
            "description": "Discuss software and web development, including Python, Flask, Django, Gunicorn, Nginx, JavaScript, Node.js, PostgreSQL, MongoDB, Git, Docker, Kubernetes, AWS, REST APIs, microservices, and agile methodologies."
        },
        {
            "_id": 2,
            "name": "Gaming",
            "description": "Explore video games, esports, and gaming culture, including Valorant, Fortnite, League of Legends, Call of Duty, aim training, streaming on Twitch, gaming PCs, PlayStation, Xbox, Nintendo Switch, and Unity game development."
        },
        {
            "_id": 3,
            "name": "Music",
            "description": "Discuss music creation and performance, including Ableton Live, FL Studio, Serum plugins, electronic music, guitar, piano, music theory, mixing, mastering, DJing, and festivals like Coachella."
        },
        {
            "_id": 4,
            "name": "Science",
            "description": "Explore scientific research, including CRISPR, quantum mechanics, biology, chemistry, astrophysics, climate science, data analysis with MATLAB, R, machine learning, and telescopes like James Webb."
        },
        {
            "_id": 5,
            "name": "Art",
            "description": "Discuss visual arts, including Procreate, Photoshop, digital painting, watercolor effects, 3D modeling with Blender, photography, graphic design, art history, and NFT art."
        },
        {
            "_id": 6,
            "name": "Sports",
            "description": "Discuss sports and fitness, including soccer, basketball, strength training, yoga, sports science, nutrition, running shoes, fitness trackers, and events like the FIFA World Cup."
        }
    ]
    mongo.db.communities.insert_many(communities)
    print("Inserted 6 communities into the database.")

if __name__ == '__main__':
    app.run(debug=True)