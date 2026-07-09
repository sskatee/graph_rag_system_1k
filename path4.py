import os
from openai import OpenAI
from qdrant_client import QdrantClient
from typing import List, Dict

# ==========================================
# Инициализация сервисов
# ==========================================

# Qdrant (Векторный поиск)
client_qdrant = QdrantClient("localhost", port=6333)

# vLLM-embedding (порт 8001)
embedding_client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8001/v1"
)

VECTOR_SIZE = 1024


# ==========================================
# Функция получения эмбеддинга
# ==========================================
def get_embedding(text: str) -> list[float]:
    """Получает векторное представление текста через vLLM-embedding."""
    try:
        response = embedding_client.embeddings.create(
            model="google/embeddinggemma-300m",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Ошибка получения эмбеддинга: {e}")
        return [0.0] * VECTOR_SIZE


# ==========================================
# Поиск в Qdrant (ИСПРАВЛЕНО: возвращает список)
# ==========================================
def search_qdrant(query: str, collection_name: str = "chunks", limit: int = 3) -> List[Dict]:
    """
    Ищет релевантные чанки в Qdrant.
    Возвращает СПИСОК словарей с результатами.
    """
    try:
        # Проверяем, существует ли коллекция
        collections = client_qdrant.get_collections().collections
        if not any(c.name == collection_name for c in collections):
            print(f"⚠️ Коллекция '{collection_name}' не найдена в Qdrant.")
            return []  # ← Возвращаем ПУСТОЙ СПИСОК

        # Получаем эмбеддинг запроса
        query_vector = get_embedding(query)

        # Ищем ближайшие векторы
        hits = client_qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )

        if not hits:
            print("Контекст в Qdrant не найден.")
            return []  # ← Возвращаем ПУСТОЙ СПИСОК

        # Формируем результаты как список словарей
        results = []
        for hit in hits:
            result = {
                "text": hit.payload.get("text", ""),
                "source": hit.payload.get("source", "unknown"),
                "page": hit.payload.get("page", ""),
                "score": hit.score
            }
            results.append(result)

        return results  # ← Возвращаем СПИСОК

    except Exception as e:
        print(f"❌ Ошибка Qdrant: {e}")
        return []  # ← Возвращаем ПУСТОЙ СПИСОК при ошибке


# ==========================================
# Запуск
# ==========================================
if __name__ == "__main__":

    test_queries = [
        "Как vLLM работает с GPU?",
        "Что такое квантование моделей?",
        "Расскажи про векторные базы данных"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"ЗАПРОС {i}: '{query}'")

        results = search_qdrant(query, collection_name="chunks", limit=3)

        if results:
            print(f"\n✅ Найдено {len(results)} релевантных чанков:\n")
            for j, result in enumerate(results, 1):
                print(f"  [{j}] Релевантность: {result['score']:.4f}")
                print(f"      Источник: {result['source']}", end="")
                if result['page']:
                    print(f" (стр. {result['page']})", end="")
                print()
                print(f"      Текст: {result['text'][:150]}...")
                print()
        else:
            print("\n️ Результаты не найдены.")

