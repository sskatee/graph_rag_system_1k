# chunk_indexer.py
import json
import os
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


def load_chunks_from_json(filepath: str) -> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    source_name = os.path.splitext(os.path.basename(filepath))[0]

    chunks = []
    for i, item in enumerate(data):
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = item.get("text", "").strip()
        else:
            continue

        if not text:
            continue

        chunks.append({
            "point_id": i + 1,
            "chunk_id": f"{source_name}_chunk_{i + 1}",
            "text": text,
            "metadata": {
                "source": source_name,
                "chunk_index": i + 1,
                "length": len(text)
            }
        })

    print(f"Загружено {len(chunks)} чанков.")
    return chunks


def index_chunks(json_path: str = None):
    if json_path is None:
        json_path = CHUNKS_INPUT_FILE

    create_chunks_collection()
    chunks = load_chunks_from_json(json_path)

    if not chunks:
        print("Нет чанков для индексации.")
        return

    texts = [chunk["text"] for chunk in chunks]
    print("Векторизация чанков...")
    embeddings = get_embeddings(texts)

    points = []
    for chunk, embedding in zip(chunks, embeddings):
        points.append(PointStruct(
            id=chunk["point_id"],
            vector=embedding,
            payload={
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                **chunk["metadata"]
            }
        ))

    qdrant.upsert(collection_name=QDRANT_CHUNKS_COLLECTION, points=points)
    print(f"Индексация завершена. Загружено {len(points)} точек.")


if __name__ == "__main__":
    index_chunks()