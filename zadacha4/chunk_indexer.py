import json
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from config import QDRANT_HOST, QDRANT_PORT, QDRANT_CHUNKS_COLLECTION, VECTOR_DIM, CHUNKS_INPUT_FILE
from embedder import get_embeddings

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def create_chunks_collection():
    collections = [c.name for c in qdrant.get_collections().collections]
    if QDRANT_CHUNKS_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=QDRANT_CHUNKS_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
        )
        print(f"Коллекция '{QDRANT_CHUNKS_COLLECTION}' создана.")
    else:
        print(f"Коллекция '{QDRANT_CHUNKS_COLLECTION}' уже существует.")


def load_chunks(filepath: str) -> list[dict]:
    """Читает JSON-массив из JSON-строк и возвращает список словарей."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw_array = json.load(f)

    chunks = []
    for item in raw_array:
        chunk = json.loads(item)
        chunks.append(chunk)

    print(f"Загружено {len(chunks)} чанков из файла.")
    return chunks


def index_chunks(jsonl_path: str = None):
    if jsonl_path is None:
        jsonl_path = CHUNKS_INPUT_FILE

    create_chunks_collection()
    chunks = load_chunks(jsonl_path)

    if not chunks:
        print("Нет чанков для индексации.")
        return

    texts = [chunk["text"] for chunk in chunks]
    print("Векторизация чанков...")
    embeddings = get_embeddings(texts)

    points = []
    for i, chunk in enumerate(chunks):
        points.append(PointStruct(
            id=i,
            vector=embeddings[i],
            payload={
                "chunk_id": chunk.get("chunk_id", f"chunk_{i}"),
                "text": chunk["text"],
                **chunk.get("metadata", {})
            }
        ))

    qdrant.upsert(collection_name=QDRANT_CHUNKS_COLLECTION, points=points)
    print(f"Индексация чанков завершена. Загружено {len(points)} точек.")


if __name__ == "__main__":
    index_chunks()