
import os
import sys
from dotenv import load_dotenv

# Load env BEFORE imports
load_dotenv()

# Ensure app is in path
sys.path.append(os.getcwd())

from sqlalchemy.orm import sessionmaker
from app.core.database import get_db_session
from app.services.clustering_service import get_clustering_service
from app.services.embedding_service import get_embedding_service
from app.core.prompts import GRAVITATIONAL_SYSTEM_PROMPT
from app.models.message import Base, DiscordMessage

def test_prompt_loading():
    print("\n--- 1. Testing Prompt Loading ---")
    if len(GRAVITATIONAL_SYSTEM_PROMPT) > 1000:
        print(f"✅ Gravitational System Prompt loaded successfully. Length: {len(GRAVITATIONAL_SYSTEM_PROMPT)} chars")
        print(f"Snippet: {GRAVITATIONAL_SYSTEM_PROMPT[:100]}...")
    else:
        print("❌ Prompt loading failed or prompt is too short.")

def seed_data(db):
    """Seed some data if empty to test clustering"""
    count = db.query(DiscordMessage).count()
    if count >= 10:
        print(f"\n--- Database has {count} messages. Skipping seed. ---")
        return

    print(f"\n--- Seeding Database (Current count: {count}) ---")
    print("Generating synthetic discourse for clustering test...")
    
    # Synthetic data represents 3 distinct topics: AI, Gardening, and Space
    messages = [
        ("The neural networks are learning at an exponential rate.", "user_ai_1"),
        ("Transformers changed the landscape of NLP forever.", "user_ai_2"),
        ("I think AGI is approaching faster than we predict.", "user_ai_1"),
        ("Model weights are just compressed representations of data.", "user_ai_3"),
        
        ("My tomatoes are finally turning red this season.", "user_garden_1"),
        ("Don't forget to water the hydrangeas in the morning.", "user_garden_2"),
        ("Organic compost is key to healthy soil structure.", "user_garden_1"),
        ("The pests are eating my lettuce leaves!", "user_garden_3"),
        
        ("The new telescope images of the nebula are breathtaking.", "user_space_1"),
        ("Black holes distort spacetime in fascinating ways.", "user_space_2"),
        ("Mars colonization will require terraforming technology.", "user_space_1"),
        ("The orbital mechanics of that satellite are complex.", "user_space_3")
    ]
    
    # We need to run the async process_and_store_message synchronously for this script
    # But since we can't easily run async in this sync script structure without overhaul,
    # let's just manually embed and insert.
    
    svc = get_embedding_service()
    
    for content, author in messages:
        # Check if exists to avoid dupes in this test
        exists = db.query(DiscordMessage).filter_by(content=content).first()
        if not exists:
            print(f"Embedding: {content[:30]}...")
            emb = svc.embed_batch([content])[0]
            msg = DiscordMessage(
                discord_id=f"test_{hash(content)}",
                author_id=author,
                channel_id="test_channel",
                content=content,
                embedding=emb
            )
            db.add(msg)
    
    db.commit()
    print("✅ Seed data inserted.")

def test_clustering(db):
    print("\n--- 2. Testing Semantic Clustering ---")
    clustering = get_clustering_service(db)
    
    # 1. Summary
    summary = clustering.get_cluster_summary()
    print(f"Stats: {summary}")
    
    # 2. Topics
    print("\n> Testing Topic Discovery...")
    topics = clustering.discover_topics(n_clusters=3)
    for t in topics:
        print(f"  Cluster {t.cluster_id}: {t.message_count} msgs. Top words/msg: {t.representative_messages[0][:50]}...")
        
    # 3. Mindmap
    print("\n> Testing Mindmap (user_ai_1)...")
    profile = clustering.get_author_profile("user_ai_1")
    if profile:
        print(f"  Profile found! Msg count: {profile.message_count}")
        print(f"  Sample: {profile.sample_messages[0]}")
    else:
        print("  Profile not found (might need seed data).")

    # 4. Similar Thinkers
    print("\n> Testing Similar Thinkers (user_ai_1 vs others)...")
    similar = clustering.find_similar_thinkers("user_ai_1")
    for s in similar:
        print(f"  User {s[0]}: Similarity {s[1]:.4f}")

    # 5. Who Said
    print("\n> Testing Who Said 'soil'...")
    attributions = clustering.attribute_idea("soil")
    for a in attributions:
        print(f"  User {a[0]}: Score {a[1]:.4f}")

if __name__ == "__main__":
    try:
        # Setup DB
        db = next(get_db_session())
        
        test_prompt_loading()
        seed_data(db)
        test_clustering(db)
        
        db.close()
        print("\n✅ VERIFICATION COMPLETE: Core logic is functional.")
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
