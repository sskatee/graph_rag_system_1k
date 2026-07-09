import os
from openai import OpenAI
from qdrant_client import QdrantClient
from gqlalchemy import Memgraph
from typing import Dict, List, Tuple

# ==========================================
# 0. Инициализация сервисов
# ==========================================

# Qdrant (Векторный поиск)
client_qdrant = QdrantClient("localhost", port=6333)

# vLLM-embedding (порт 8001 из docker-compose.yml)
# Используем библиотеку openai, так как vLLM эмулирует OpenAI API
embedding_client = OpenAI(
    api_key="EMPTY",  # Для локального vLLM ключ не нужен
    base_url="http://localhost:8001/v1"
)

VECTOR_SIZE = 1024  # Размерность эмбеддингов для google/embeddinggemma-300m

# Memgraph (Граф)
memgraph = Memgraph("localhost", 7687)

# 1. Функция получения эмбеддинга
def get_embedding(text: str) -> list[float]:
    """
    Получает векторное представление текста через vLLM-embedding.
    """
    try:
        response = embedding_client.embeddings.create(
            model="google/embeddinggemma-300m",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Ошибка получения эмбеддинга: {e}")
        # Возвращаем нулевой вектор в случае ошибки (для тестов)
        return [0.0] * VECTOR_SIZE


# ==========================================
# 2. Сериализация подграфа в текст
# ==========================================
def serialize_subgraph_to_text(subgraph: Dict[str, List]) -> str:
    """
    Превращает структуру подграфа в текст, понятный для LLM.
    """
    if not subgraph["nodes"] and not subgraph["edges"]:
        return "Связи в графовой базе не найдены."

    text = "📊 **Контекст из графовой базы знаний (Memgraph):**\n"

    # Список сущностей
    text += f"Найдено сущностей: {len(subgraph['nodes'])}\n"
    for node in subgraph["nodes"]:
        labels = ", ".join(node.get("labels", []))
        text += f"- {node['name']} (тип: {labels})\n"

    # Список связей (триплеты)
    text += f"\nНайдено связей: {len(subgraph['edges'])}\n"
    for edge in subgraph["edges"]:
        # Находим имена узлов по ID для красивого вывода
        from_name = next((n["name"] for n in subgraph["nodes"] if n["id"] == edge["from"]), "unknown")
        to_name = next((n["name"] for n in subgraph["nodes"] if n["id"] == edge["to"]), "unknown")

        text += f"- {from_name} --[{edge['relation']}]--> {to_name}"
        if edge.get("evidence") and edge["evidence"] != "unknown":
            text += f" *(источник: {edge['evidence']})*"
        text += "\n"

    return text


# ==========================================
# 3. Поиск в Qdrant (Векторный контекст)
# ==========================================
def search_qdrant(query: str, collection_name: str = "chunks", limit: int = 3) -> str:
    """
    Ищет релевантные чанки в Qdrant через семантический поиск.
    """
    try:
        # Проверяем, существует ли коллекция
        collections = client_qdrant.get_collections().collections
        if not any(c.name == collection_name for c in collections):
            return "⚠️ Qdrant: Коллекция не найдена (данные еще не загружены)."

        # Получаем эмбеддинг запроса через vLLM-embedding (порт 8001)
        query_vector = get_embedding(query)

        # Ищем ближайшие векторы в Qdrant
        hits = client_qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )

        if not hits:
            return "Контекст в Qdrant не найден."

        # Формируем текст из найденных чанков
        results = []
        for hit in hits:
            text = hit.payload.get("text", "")
            source = hit.payload.get("source", "unknown")
            page = hit.payload.get("page", "")
            score = hit.score

            result_text = f"- {text} (источник: {source}"
            if page:
                result_text += f", стр. {page}"
            result_text += f", релевантность: {score:.3f})"
            results.append(result_text)

        return "\n".join(results)

    except Exception as e:
        return f"⚠️ Ошибка Qdrant: {e}"



