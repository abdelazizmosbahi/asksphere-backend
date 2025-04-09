from app import app, mongo

# Populate the database with initial communities
with app.app_context():
    # Clear existing communities
    mongo.db.communities.drop()

    # Insert 6 communities with detailed descriptions
    communities = [
        {
            "_id": 1,
            "name": "Development",
            "description": "A community dedicated to software developers, programmers, and coding enthusiasts. Discuss topics like programming languages such as Python, Java, JavaScript, C++, and Ruby; web development frameworks including Django, Flask, React, and Angular; backend tools like Node.js and Express; version control systems such as Git and GitHub; software development methodologies like Agile and DevOps; debugging techniques, code optimization, and best practices; integrated development environments (IDEs) like VS Code, IntelliJ, and PyCharm; database management with SQL, MongoDB, or PostgreSQL; and career advice for programmers, including job interviews, portfolio building, and freelancing."
        },
        {
            "_id": 2,
            "name": "Gaming",
            "description": "A community for gamers passionate about video games across all platforms. Share insights on popular titles like Fortnite, Call of Duty, The Legend of Zelda, and Cyberpunk 2077; discuss gaming hardware such as PlayStation, Xbox, Nintendo Switch, and PC builds with GPUs like NVIDIA RTX or AMD Ryzen; explore esports tournaments, strategies, and professional gaming; exchange tips and tricks for improving gameplay, mastering combos, or speedrunning; talk about game development with engines like Unity or Unreal Engine; and dive into gaming culture, including retro games, mods, virtual reality (VR), and streaming on Twitch or YouTube."
        },
        {
            "_id": 3,
            "name": "Music",
            "description": "A community for music lovers, musicians, and producers to connect. Explore genres like rock, hip-hop, classical, jazz, electronic, and pop; discuss favorite artists, albums, and songs from The Beatles to Billie Eilish; share techniques for playing instruments such as guitar, piano, drums, violin, or synthesizer; dive into music production with software like Ableton Live, FL Studio, or Logic Pro, including mixing, mastering, and sound design; talk about music theory, composition, and songwriting; and exchange experiences from live concerts, festivals, vinyl collecting, or creating playlists on Spotify and Apple Music."
        },
        {
            "_id": 4,
            "name": "Science",
            "description": "A community for science enthusiasts, researchers, and students to explore the wonders of the natural world. Discuss physics topics like quantum mechanics, relativity, and astrophysics; chemistry concepts such as organic reactions, periodic table trends, and lab techniques; biology areas including genetics, evolution, and microbiology; astronomy subjects like black holes, exoplanets, and telescopes; cutting-edge research in AI, nanotechnology, and climate science; scientific experiments, data analysis with tools like MATLAB or Python’s SciPy; and science communication, including journals, documentaries, or teaching complex ideas to the public."
        },
        {
            "_id": 5,
            "name": "Art",
            "description": "A community for artists, designers, and creatives to showcase and discuss their work. Explore traditional art mediums like painting with oils or watercolors, drawing with pencils or charcoal, and sculpting with clay or metal; dive into digital art using tools like Adobe Photoshop, Illustrator, Procreate, or Blender for 3D modeling; share techniques for portraiture, landscape art, abstract styles, or animation; discuss photography with DSLR cameras, editing in Lightroom, or composition tips; and talk about art history, inspiration from movements like Renaissance or Surrealism, and creative careers in graphic design or illustration."
        },
        {
            "_id": 6,
            "name": "Sports",
            "description": "A community for sports fans, athletes, and fitness enthusiasts to engage. Discuss popular sports like basketball, soccer, football, tennis, baseball, and hockey; share training routines for strength, endurance, or agility using weights, cardio, or yoga; explore strategies and techniques like shooting hoops, perfecting a serve, or hitting a home run; talk about professional leagues such as the NBA, NFL, or FIFA World Cup, including players like LeBron James or Lionel Messi; exchange gear recommendations for running shoes, tennis rackets, or gym equipment; and dive into sports nutrition, injury recovery, and fan experiences at live events."
        }
    ]
    mongo.db.communities.insert_many(communities)
    print("Inserted 6 communities into the database.")

if __name__ == '__main__':
    app.run(debug=True)