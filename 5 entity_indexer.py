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
    collections = [c.name for c in qdrant.get_collections().collections]
    if QDRANT_ENTITIES_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=QDRANT_ENTITIES_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
        )
        print(f"Коллекция '{QDRANT_ENTITIES_COLLECTION}' создана.")
    else:
        print(f"Коллекция '{QDRANT_ENTITIES_COLLECTION}' уже существует.")


def fetch_entities_from_memgraph() -> list[dict]:
    driver = GraphDatabase.driver(MEMGRAPH_URI, auth=("memgraph", "memgraph"))
    entities = []

    with driver.session() as session:
        # Изменено: e.description вместо e.desc
        result = session.run(
            "MATCH (e:Entity) "
            "WHERE e.description IS NOT NULL AND e.description <> '' "
            "RETURN e.id AS entity_id, e.name AS name, "
            "e.description AS description, e.type AS type "
            "LIMIT 100"
        )

        for record in result:
            entity_id = record.get("entity_id")
            name = record.get("name") or ""
            description = record.get("description") or ""
            entity_type = record.get("type") or "Unknown"

            if not entity_type or entity_type == "Unknown":
                label_result = session.run(
                    "MATCH (e:Entity {id: $id}) RETURN labels(e) AS labels",
                    {"id": entity_id}
                )
                label_record = label_result.single()
                if label_record and label_record["labels"]:
                    labels = [l for l in label_record["labels"] if l != "Entity"]
                    if labels:
                        entity_type = labels[0]

            entities.append({
                "entity_id": str(entity_id),
                "name": name,
                "description": description,
                "type": entity_type
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

    points = []
    for i, entity in enumerate(entities):
        points.append(PointStruct(
            id=i + 1,  # числовой ID
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