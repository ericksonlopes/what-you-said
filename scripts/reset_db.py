import sys
import os
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para importar os módulos internos
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.append(str(root))

from src.infrastructure.repositories.sql.connector import engine, Base
from src.config.settings import settings
import weaviate

def reset_sql():
    print("--- Cleaning SQL Database ---")
    try:
        # Import models to ensure they are registered with Base
        from src.infrastructure.repositories.sql.models.knowledge_subject import KnowledgeSubjectModel
        from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel
        from src.infrastructure.repositories.sql.models.ingestion_job import IngestionJobModel
        from src.infrastructure.repositories.sql.models.chunk_index import ChunkIndexModel

        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables.")
        Base.metadata.create_all(bind=engine)
        print("Recreated all tables.")
        print("✅ SQL Database reset complete.")
    except Exception as e:
        print(f"❌ Error resetting SQL: {e}")

def reset_weaviate():
    print(f"--- Cleaning Weaviate at {settings.vector.weaviate_host} ---")
    try:
        import weaviate
        from weaviate.classes.init import AdditionalConfig, Timeout

        # Connect to Weaviate v4
        client = weaviate.connect_to_local(
            host=settings.vector.weaviate_host,
            port=settings.vector.weaviate_port,
            grpc_port=50051,
            additional_config=AdditionalConfig(
                timeout=Timeout(query=60, insert=120, init=30)
            )
        )

        try:
            # List all collections
            collections = client.collections.list_all()

            if not collections:
                print("No collections found in Weaviate.")
            else:
                for collection_name in collections:
                    print(f"Deleting collection: {collection_name}")
                    client.collections.delete(collection_name)

            print("✅ Weaviate reset complete.")
        finally:
            client.close()

    except Exception as e:
        print(f"❌ Error connecting to Weaviate: {e}")
def main():
    print("⚠️  WARNING: This will DELETE ALL DATA in SQL and Weaviate! ⚠️")
    confirm = input("Are you absolutely sure? (y/N): ")
    if confirm.lower() == 'y':
        reset_sql()
        reset_weaviate()
        print("\n🚀 System is clean and ready for a fresh start!")
    else:
        print("Operation aborted.")

if __name__ == "__main__":
    main()
