import json
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from config import QDRANT_HOST, QDRANT_PORT, QDRANT_CHUNKS_COLLECTION, VECTOR_DIM, CHUNKS_INPUT_FILE
from embedder import get_embeddings

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def create_chunks_collection():
    """Создаёт коллекцию, если её нет."""
    collections = [c.name for c in qdrant.get_collections().collections]
    if QDRANT_CHUNKS_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=QDRANT_CHUNKS_COLLECTION,
            vectors_config=VectorParams(
                size=VECTOR_DIM,
                distance=Distance.COSINE
            )
        )
        print(f"Коллекция '{QDRANT_CHUNKS_COLLECTION}' создана.")
    else:
        print(f"Коллекция '{QDRANT_CHUNKS_COLLECTION}' уже существует.")


def index_chunks(jsonl_path: str = None):
    """Полная индексация чанков из JSONL-файла."""
    if jsonl_path is None:
        jsonl_path = CHUNKS_INPUT_FILE

    create_chunks_collection()

    # Читаем все чанки
    chunks = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    if not chunks:
        print("Нет чанков для индексации. Файл пуст.")
        return

    print(f"Загружено {len(chunks)} чанков. Начинаю векторизацию...")

    # Извлекаем тексты
    texts = [chunk["text"] for chunk in chunks]

    # Векторизуем
    embeddings = get_embeddings(texts)

    # Формируем точки для Qdrant
    points = []
    for i, chunk in enumerate(chunks):
        points.append(PointStruct(
            id=i,  # или chunk["chunk_id"] если он числовой/строковый
            vector=embeddings[i],
            payload={
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                **chunk.get("metadata", {})
            }
        ))

    # Загружаем в Qdrant (upsert — обновит существующие точки с теми же id)
    qdrant.upsert(collection_name=QDRANT_CHUNKS_COLLECTION, points=points)
    print(f"Индексация чанков завершена. Загружено {len(points)} точек.")


if __name__ == "__main__":
    index_chunks()