# fix_qdrant_dimensions.py
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient("localhost", port=6333)

# Правильная размерность для all-MiniLM-L6-v2
CORRECT_DIM = 768

# Список коллекций
collections_to_fix = ["chunks", "entities"]

print("🔧 Пересоздание коллекций с размерностью 384...")

for collection_name in collections_to_fix:
    try:
        # Удаляем
        client.delete_collection(collection_name)
        print(f"  ✅ Коллекция '{collection_name}' удалена")
    except Exception as e:
        print(f"  ⚠️ Не удалось удалить '{collection_name}': {e}")

    # Создаем с правильной размерностью
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=CORRECT_DIM,
            distance=Distance.COSINE
        )
    )
    print(f"  ✅ Коллекция '{collection_name}' создана с размерностью {CORRECT_DIM}")

print("\n📊 Проверка:")
for collection_name in collections_to_fix:
    try:
        info = client.get_collection(collection_name)
        print(f"  {collection_name}: размерность {info.config.params.vectors.size}")
    except:
        print(f"  {collection_name}: не найдена")