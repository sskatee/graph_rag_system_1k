from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from config import (
    QDRANT_HOST, QDRANT_PORT, QDRANT_ENTITIES_COLLECTION,
    MEMGRAPH_URI, VECTOR_DIM
)
from embedder import get_embeddings

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def create_entities_collection():
    """Создаёт коллекцию для сущностей."""
    collections = [c.name for c in qdrant.get_collections().collections]
    if QDRANT_ENTITIES_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=QDRANT_ENTITIES_COLLECTION,
            vectors_config=VectorParams(
                size=VECTOR_DIM,
                distance=Distance.COSINE
            )
        )
        print(f"Коллекция '{QDRANT_ENTITIES_COLLECTION}' создана.")
    else:
        print(f"Коллекция '{QDRANT_ENTITIES_COLLECTION}' уже существует.")


def fetch_entities_from_memgraph() -> list[dict]:
    driver = GraphDatabase.driver(MEMGRAPH_URI, auth=("memgraph", "memgraph"))
    entities = []

    with driver.session() as session:
        result = session.run(
            "MATCH (e:Entity) "
            "WHERE e.desc IS NOT NULL "  # <-- было e.description, стало e.desc
            "RETURN e.id AS entity_id, e.name AS name, "
            "e.desc AS description, labels(e) AS labels"  # <-- и здесь e.desc
        )
        for record in result:
            entities.append({
                "entity_id": str(record["entity_id"]),
                "name": record["name"] or "",
                "description": record["description"] or "",
                "type": record["labels"][0] if record["labels"] else "Unknown"
            })

    driver.close()
    print(f"Извлечено {len(entities)} сущностей из Memgraph.")
    return entities


def index_entities():
    """Полная индексация сущностей из Memgraph."""
    create_entities_collection()

    entities = fetch_entities_from_memgraph()

    if not entities:
        print("Нет сущностей для индексации.")
        return

    # Готовим тексты для эмбеддинга: имя + описание
    texts = [f"{e['name']}: {e['description']}" for e in entities]

    print("Векторизация сущностей...")
    embeddings = get_embeddings(texts)

    # Формируем точки
    points = []
    for i, entity in enumerate(entities):
        points.append(PointStruct(
            id=entity["entity_id"],  # ID из Memgraph для связи с графом!
            vector=embeddings[i],
            payload={
                "entity_id": entity["entity_id"],
                "name": entity["name"],
                "description": entity["description"],
                "type": entity["type"]
            }
        ))

    qdrant.upsert(collection_name=QDRANT_ENTITIES_COLLECTION, points=points)
    print(f"Индексация сущностей завершена. Загружено {len(points)} точек.")


if __name__ == "__main__":
    index_entities()