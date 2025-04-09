from sentence_transformers import SentenceTransformer, util

# Load the four models
models = {
    "all-MiniLM-L6-v2": SentenceTransformer('all-MiniLM-L6-v2'),
    "all-distilroberta-v1": SentenceTransformer('all-distilroberta-v1'),
    "all-mpnet-base-v2": SentenceTransformer('all-mpnet-base-v2'),
    "multi-qa-mpnet-base-dot-v1": SentenceTransformer('multi-qa-mpnet-base-dot-v1')
}

# Your community descriptions from run.py
communities = [
    {
        "id": 1,
        "name": "Development",
        "description": "A community dedicated to software developers, programmers, and coding enthusiasts. Discuss topics like programming languages such as Python, Java, JavaScript, C++, and Ruby; web development frameworks including Django, Flask, React, and Angular; backend tools like Node.js and Express; version control systems such as Git and GitHub; software development methodologies like Agile and DevOps; debugging techniques, code optimization, and best practices; integrated development environments (IDEs) like VS Code, IntelliJ, and PyCharm; database management with SQL, MongoDB, or PostgreSQL; and career advice for programmers, including job interviews, portfolio building, and freelancing."
    },
    {
        "id": 2,
        "name": "Gaming",
        "description": "A community for gamers passionate about video games across all platforms. Share insights on popular titles like Fortnite, Call of Duty, The Legend of Zelda, and Cyberpunk 2077; discuss gaming hardware such as PlayStation, Xbox, Nintendo Switch, and PC builds with GPUs like NVIDIA RTX or AMD Ryzen; explore esports tournaments, strategies, and professional gaming; exchange tips and tricks for improving gameplay, mastering combos, or speedrunning; talk about game development with engines like Unity or Unreal Engine; and dive into gaming culture, including retro games, mods, virtual reality (VR), and streaming on Twitch or YouTube."
    },
    {
        "id": 3,
        "name": "Music",
        "description": "A community for music lovers, musicians, and producers to connect. Explore genres like rock, hip-hop, classical, jazz, electronic, and pop; discuss favorite artists, albums, and songs from The Beatles to Billie Eilish; share techniques for playing instruments such as guitar, piano, drums, violin, or synthesizer; dive into music production with software like Ableton Live, FL Studio, or Logic Pro, including mixing, mastering, and sound design; talk about music theory, composition, and songwriting; and exchange experiences from live concerts, festivals, vinyl collecting, or creating playlists on Spotify and Apple Music."
    },
    {
        "id": 4,
        "name": "Science",
        "description": "A community for science enthusiasts, researchers, and students to explore the wonders of the natural world. Discuss physics topics like quantum mechanics, relativity, and astrophysics; chemistry concepts such as organic reactions, periodic table trends, and lab techniques; biology areas including genetics, evolution, and microbiology; astronomy subjects like black holes, exoplanets, and telescopes; cutting-edge research in AI, nanotechnology, and climate science; scientific experiments, data analysis with tools like MATLAB or Python’s SciPy; and science communication, including journals, documentaries, or teaching complex ideas to the public."
    },
    {
        "id": 5,
        "name": "Art",
        "description": "A community for artists, designers, and creatives to showcase and discuss their work. Explore traditional art mediums like painting with oils or watercolors, drawing with pencils or charcoal, and sculpting with clay or metal; dive into digital art using tools like Adobe Photoshop, Illustrator, Procreate, or Blender for 3D modeling; share techniques for portraiture, landscape art, abstract styles, or animation; discuss photography with DSLR cameras, editing in Lightroom, or composition tips; and talk about art history, inspiration from movements like Renaissance or Surrealism, and creative careers in graphic design or illustration."
    },
    {
        "id": 6,
        "name": "Sports",
        "description": "A community for sports fans, athletes, and fitness enthusiasts to engage. Discuss popular sports like basketball, soccer, football, tennis, baseball, and hockey; share training routines for strength, endurance, or agility using weights, cardio, or yoga; explore strategies and techniques like shooting hoops, perfecting a serve, or hitting a home run; talk about professional leagues such as the NBA, NFL, or FIFA World Cup, including players like LeBron James or Lionel Messi; exchange gear recommendations for running shoes, tennis rackets, or gym equipment; and dive into sports nutrition, injury recovery, and fan experiences at live events."
    }
]

# Test contents
test_contents = [
    "What’s the best Python framework for web development?",      # Relevant
    "How do I use Git for version control?",                     # Relevant
    "What’s a good IDE for Java programming?",                   # Relevant
    "How do I improve my jump shot in basketball?",             # Irrelevant (Sports)
    "Any tips for mixing electronic music tracks?",             # Irrelevant (Music)
    "Random text about nothing specific.",                      # Irrelevant
    "What’s the weather like today?"                            # Irrelevant
]

# Encode the Development description for each model
dev_desc = communities[0]["description"]
embeddings = {name: model.encode(dev_desc, convert_to_tensor=True) for name, model in models.items()}

# Test each model
for model_name, model in models.items():
    print(f"\nTesting with {model_name}:")
    for content in test_contents:
        content_embedding = model.encode(content, convert_to_tensor=True)
        score = util.cos_sim(content_embedding, embeddings[model_name])[0][0].item()
        print(f"Content: '{content}'\nSimilarity Score: {score:.4f}\n")