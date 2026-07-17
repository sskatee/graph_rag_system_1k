# test_search.py
from search_api import search_chunks, search_entities

# Тест поиска по чанкам
print("=== Поиск по чанкам: 'архитектура Graph-RAG' ===")
results = search_chunks("архитектура Graph-RAG", top_k=3)
for i, r in enumerate(results):
    print(f"\n--- Результат {i+1} (score: {r['score']:.4f}) ---")
    print(f"ID: {r['chunk_id']}")
    print(f"Текст: {r['text'][:200]}...")
    print(f"Метаданные: {r['metadata']}")

# Тест поиска по сущностям
print("\n\n=== Поиск по сущностям: 'векторная база данных' ===")
results = search_entities("векторная база данных", top_k=3)
for i, r in enumerate(results):
    print(f"\n--- Результат {i+1} (score: {r['score']:.4f}) ---")
    print(f"Сущность: {r['name']} (тип: {r['type']})")
    print(f"Описание: {r['description'][:150]}...")
    print(f"entity_id: {r['entity_id']}")