# search_api.py
from qdrant_client import QdrantClient
from config import QDRANT_HOST, QDRANT_PORT, QDRANT_CHUNKS_COLLECTION, QDRANT_ENTITIES_COLLECTION
from embedder import get_single_embedding

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def search_chunks(query: str, top_k: int = 5) -> list[dict]:
    """
    Поиск релевантных чанков по текстовому запросу.
    Возвращает список словарей с ключами: chunk_id, text, score, metadata.
    """
    query_vector = get_single_embedding(query)

    results = qdrant.search(
        collection_name=QDRANT_CHUNKS_COLLECTION,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )

    return [
        {
            "chunk_id": hit.payload["chunk_id"],
            "text": hit.payload["text"],
            "score": hit.score,
            "metadata": {
                k: v for k, v in hit.payload.items()
                if k not in ("chunk_id", "text")
            }
        }
        for hit in results
    ]


def search_entities(query: str, top_k: int = 5) -> list[dict]:
    """
    Поиск релевантных сущностей по текстовому запросу.
    Возвращает список словарей с ключами: entity_id, name, description, type, score.
    entity_id можно использовать для запросов в Memgraph (задача №5).
    """
    query_vector = get_single_embedding(query)

    results = qdrant.search(
        collection_name=QDRANT_ENTITIES_COLLECTION,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )

    return [
        {
            "entity_id": hit.payload["entity_id"],
            "name": hit.payload["name"],
            "description": hit.payload["description"],
            "type": hit.payload["type"],
            "score": hit.score
        }
        for hit in results
    ]