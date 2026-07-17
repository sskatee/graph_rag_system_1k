import os
from openai import OpenAI
from qdrant_client import QdrantClient
from typing import List, Dict
import requests

# ==========================================
# Инициализация сервисов
# ==========================================

# Qdrant (Векторный поиск)
client_qdrant = QdrantClient("localhost", port=6333)

# vLLM-embedding - ИСПРАВЛЕНО: порт 8000 вместо 8001
VLLM_HOST = "http://localhost:8001"  # <-- ИЗМЕНЕНО
VLLM_MODEL = "google/embeddinggemma-300m"
VECTOR_SIZE = 768  # Размерность для google/embeddinggemma-300m

# Создаем клиент один раз
embedding_client = OpenAI(
    api_key="EMPTY",
    base_url=f"{VLLM_HOST}/v1"  # <-- ИСПРАВЛЕНО: добавлен /v1
)


# ==========================================
# Функция получения эмбеддинга с проверкой сервера
# ==========================================
def get_embedding(text: str) -> list[float]:
    """Получает векторное представление текста через vLLM-embedding."""
    try:
        # Проверяем базовое соединение с сервером
        try:
            resp = requests.get(f"{VLLM_HOST}/health", timeout=5)
            if resp.status_code == 200:
                print("✅ vLLM сервер доступен")
            else:
                print(f"⚠️ vLLM ответил с кодом {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ vLLM сервер не отвечает на {VLLM_HOST}")
            print("   Проверьте: docker ps | grep vllm")
            print("   И логи: docker logs vllm_embedding")
            return [0.0] * VECTOR_SIZE

        # Получаем эмбеддинг
        response = embedding_client.embeddings.create(
            model=VLLM_MODEL,
            input=text
        )
        if response and response.data:
            embedding = response.data[0].embedding
            # Проверяем размерность
            if len(embedding) != VECTOR_SIZE:
                print(f"⚠️ Размерность не совпадает: {len(embedding)} вместо {VECTOR_SIZE}")
                # Обрезаем или дополняем
                if len(embedding) > VECTOR_SIZE:
                    embedding = embedding[:VECTOR_SIZE]
                elif len(embedding) < VECTOR_SIZE:
                    embedding = embedding + [0.0] * (VECTOR_SIZE - len(embedding))
            return embedding
        else:
            print("⚠️ Пустой ответ от сервера эмбеддингов")
            return [0.0] * VECTOR_SIZE
    except Exception as e:
        print(f"❌ Ошибка получения эмбеддинга: {e}")
        import traceback
        traceback.print_exc()
        return [0.0] * VECTOR_SIZE


# ==========================================
# Поиск в Qdrant (упрощенная версия)
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
            return []

        # Получаем эмбеддинг запроса
        query_vector = get_embedding(query)

        # Проверяем, что эмбеддинг не нулевой
        if all(v == 0.0 for v in query_vector):
            print("⚠️ Получен нулевой вектор, поиск невозможен")
            return []

        # Ищем ближайшие векторы
        search_result = client_qdrant.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit
        )

        if not search_result:
            print("Контекст в Qdrant не найден.")
            return []

        # Извлекаем точки
        points = []
        if hasattr(search_result, 'points'):
            points = search_result.points
        elif isinstance(search_result, dict):
            points = search_result.get('points', [])
        elif isinstance(search_result, (list, tuple)):
            points = search_result

        if not points:
            print("Контекст в Qdrant не найден (пустой список точек).")
            return []

        # Формируем результаты
        results = []
        for point in points:
            # Извлекаем payload и score
            payload = {}
            score = 0.0

            if hasattr(point, 'payload'):
                payload = point.payload
                score = getattr(point, 'score', 0.0)
            elif isinstance(point, dict):
                payload = point.get('payload', {})
                score = point.get('score', 0.0)
            elif isinstance(point, tuple):
                # Формат: (id, score, payload) или (id, payload, score)
                if len(point) >= 3:
                    if isinstance(point[1], dict):
                        payload = point[1]
                        score = point[2] if len(point) > 2 else 0.0
                    elif isinstance(point[2], dict):
                        payload = point[2]
                        score = point[1]
                elif len(point) == 2:
                    if isinstance(point[1], dict):
                        payload = point[1]
                    else:
                        score = point[1]

            # Преобразуем payload в словарь
            if hasattr(payload, 'dict'):
                payload = payload.dict()
            elif hasattr(payload, '__dict__'):
                payload = payload.__dict__

            if not isinstance(payload, dict):
                payload = {}

            result = {
                "text": payload.get("text", ""),
                "source": payload.get("source", "unknown"),
                "page": str(payload.get("page", "")),
                "score": float(score)
            }
            results.append(result)

        return results

    except Exception as e:
        print(f"❌ Ошибка Qdrant: {e}")
        import traceback
        traceback.print_exc()
        return []


# ==========================================
# Запуск
# ==========================================
if __name__ == "__main__":

    print("=" * 50)
    print("🔍 Проверка сервисов...")
    print("=" * 50)

    # Проверка Qdrant
    try:
        collections = client_qdrant.get_collections()
        print(f"✅ Qdrant доступен. Коллекции: {[c.name for c in collections.collections]}")
    except Exception as e:
        print(f"❌ Qdrant недоступен: {e}")

    # Проверка vLLM
    try:
        resp = requests.get(f"{VLLM_HOST}/health", timeout=5)
        if resp.status_code == 200:
            print(f"✅ vLLM доступен на {VLLM_HOST}")
        else:
            print(f"⚠️ vLLM ответил с кодом {resp.status_code}")
    except Exception as e:
        print(f"❌ vLLM недоступен: {e}")

    # Проверка эмбеддинга
    try:
        test_embed = get_embedding("test")
        if any(v != 0.0 for v in test_embed):
            print(f"✅ Эмбеддинг получен. Размерность: {len(test_embed)}")
        else:
            print("⚠️ vLLM вернул нулевой вектор")
    except Exception as e:
        print(f"❌ Ошибка получения эмбеддинга: {e}")

    print("\n" + "=" * 50)

    test_queries = [
        "Государственная дума",
        "Когда была первая русская революция?",
        "Что такое самодержавие?"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 ЗАПРОС {i}: '{query}'")
        print("-" * 40)

        results = search_qdrant(query, collection_name="chunks", limit=3)

        if results:
            print(f"\n✅ Найдено {len(results)} релевантных чанков:\n")
            for j, result in enumerate(results, 1):
                print(f"  [{j}] Релевантность: {result['score']:.4f}")
                print(f"      Источник: {result['source']}", end="")
                if result['page']:
                    print(f" (стр. {result['page']})", end="")
                print()
                print(f"      Текст: {result['text'][:150]}..." if result['text'] else "      Текст: <пусто>")
                print()
        else:
            print("\n❌ Результаты не найдены.")

res = get_embedding("fnfsnffgnfg")
print(len(res))