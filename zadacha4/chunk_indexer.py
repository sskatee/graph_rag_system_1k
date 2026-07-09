# chunk_indexer.py
import json
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from config import QDRANT_HOST, QDRANT_PORT, QDRANT_CHUNKS_COLLECTION, VECTOR_DIM, CHUNKS_INPUT_FILE
from embedder import get_embeddings

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def create_chunks_collection():
    """Создаёт коллекцию для чанков, если её нет."""
    collections = [c.name for c in qdrant.get_collections().collections]
    if QDRANT_CHUNKS_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=QDRANT_CHUNKS_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
        )
        print(f"Коллекция '{QDRANT_CHUNKS_COLLECTION}' создана.")
    else:
        print(f"Коллекция '{QDRANT_CHUNKS_COLLECTION}' уже существует.")


def load_chunks_from_json(filepath: str) -> list[dict]:
    """
    Читает JSON от задачи №1 и возвращает плоский список чанков
    с глобально уникальными ID.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    for doc in data.get("documents", []):
        filename = doc["filename"]
        file_type = doc["file_type"]

        for chunk in doc.get("chunks", []):
            # Создаём глобально уникальный ID: имя_файла + номер чанка
            global_chunk_id = f"{filename}_chunk_{chunk['chunk_id']}"

            chunks.append({
                "chunk_id": global_chunk_id,
                "text": chunk["text"],
                "metadata": {
                    "source": filename,
                    "file_type": file_type,
                    "local_chunk_id": chunk["chunk_id"],
                    "length": chunk.get("length", len(chunk["text"])),
                    "sentences_count": chunk.get("sentences_count", 0)
                }
            })

    print(f"Загружено {len(chunks)} чанков из {len(data.get('documents', []))} документов.")
    return chunks


def index_chunks(json_path: str = None):
    """
    Полная индексация чанков из JSON-файла задачи №1.
    """
    if json_path is None:
        json_path = CHUNKS_INPUT_FILE

    create_chunks_collection()
    chunks = load_chunks_from_json(json_path)

    if not chunks:
        print("Нет чанков для индексации.")
        return

    # Извлекаем тексты для векторизации
    texts = [chunk["text"] for chunk in chunks]

    print("Векторизация чанков...")
    embeddings = get_embeddings(texts)

    # Формируем точки для Qdrant
    points = []
    for i, chunk in enumerate(chunks):
        points.append(PointStruct(
            id=chunk["chunk_id"],  # строковый ID — Qdrant такое поддерживает
            vector=embeddings[i],
            payload={
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                **chunk["metadata"]
            }
        ))

    # Загружаем в Qdrant
    qdrant.upsert(collection_name=QDRANT_CHUNKS_COLLECTION, points=points)
    print(f"Индексация чанков завершена. Загружено {len(points)} точек.")


if __name__ == "__main__":
    index_chunks()