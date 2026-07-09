import os
import re
import json
from typing import Dict, List
from openai import OpenAI
from qdrant_client import QdrantClient
from gqlalchemy import Memgraph

# Импорт функций

from path1 import extract_entities  # Файл с кодом извлечения сущностей (DeepSeek)
from path2 import find_nodes_in_graph  # Файл с поиском узлов в Memgraph
from path3 import build_subgraph, serialize_subgraph_to_text  # Файл с обходом графа
from path4 import  search_qdrant #Файл с обходом векторной бд

# Инициализация клиента DeepSeek для финального ответа
os.environ['DEEPSEEK_API_KEY'] = 'sk-beb0645699024d40abc08597b1ddb64d'
client_llm = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

client_qdrant = QdrantClient("localhost", port=6333)
memgraph = Memgraph("localhost", 7687)



def generate_final_answer(query: str, graph_context: str) -> str:
    """
    Отправляет финальный промпт в DeepSeek, используя собранный графовый контекст.
    """
    system_prompt = """
    Ты — интеллектуальный ассистент Graph-RAG системы. 
    Отвечай на вопрос пользователя, опираясь СТРОГО на предоставленный контекст из графовой базы знаний.
    Если в контексте нет ответа, честно скажи об этом.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Вопрос: {query}\n\nКонтекст из графа:\n{graph_context}"}
    ]

    try:
        response = client_llm.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            temperature=0.3,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка генерации: {e}"


def run_graph_rag_pipeline(user_query: str):
    """
    Главная функция-оркестратор. Собирает все этапы воедино.
    """
    print(f"\n Запуск пайплайна для запроса: '{user_query}'\n")

    # ЭТАП 1: Извлечение сущностей
    print("[1/4] Извлечение сущностей...")
    entities = extract_entities(user_query)
    print(f" Сущности: {entities}")
    if not entities:
        print("⚠️ Сущности не найдены. Пропускаем графовый поиск.")
        return generate_final_answer(user_query, "Контекст не найден.")

    # ЭТАП 2: Поиск сущностей в графе (Mention Matching)
    print("\n[2/4] Поиск в базах данных...")
    # 2.1. Векторный поиск в Qdrant
    print("   🔍 Поиск в Qdrant (векторный поиск)...")
    qdrant_results = search_qdrant(user_query, collection_name="chunks", limit=3)
    qdrant_context = qdrant_results if qdrant_results else "Контекст не найден."
    print(f"   ✅ Найдено результатов в Qdrant: {len(qdrant_results) if qdrant_results else 0}")

    # 2.2. Графовый поиск в Memgraph
    print("    Поиск в Memgraph (графовый поиск)...")
    found_nodes = find_nodes_in_graph(entities) if entities else []
    for node in found_nodes:
        print(f" - ID: {node['internal_id']}, Имя: {node['canonical_name']}, Типы: {node['types']}")
    print(f"   ✅ Найдено узлов в Memgraph: {len(found_nodes)}")

    if not found_nodes:
        print("️ Узлы не найдены в Memgraph. Пропускаем обход.")
        return generate_final_answer(user_query, "Сущности не найдены в бд.")

    if not qdrant_context:
        print("️ Узлы не найдены в Qdrant. Пропускаем обход.")
        return generate_final_answer(user_query, "Сущности не найдены в бд .")

    # ЭТАП 3: Обход графа и сборка подграфа
    print("\n[3/4] Обход графа и сборка подграфа...")
    subgraph = build_subgraph(found_nodes, neighbor_depth=1, find_paths_between=True)

    # Сериализация подграфа в текст
    graph_text = serialize_subgraph_to_text(subgraph)

    # ЭТАП 4: Генерация финального ответа
    print("\n[4/4] Генерация финального ответа через DeepSeek...")
    final_answer = generate_final_answer(user_query, graph_text)

    print("\n" + "=" * 60)
    print("✅ ФИНАЛЬНЫЙ ОТВЕТ СИСТЕМЫ:")
    print("=" * 60)
    print(final_answer)
    print("=" * 60 + "\n")

    return final_answer


# ==========================================
# Точка входа
# ==========================================
if __name__ == "__main__":
    print(" Graph-RAG Система запущена. Введите 'exit' для выхода.")

    # Интерактивный цикл для удобного тестирования
    while True:
        query = input("\n Задайте вопрос: ")
        if query.lower() in ['exit', 'выход', 'q']:
            print("Завершение работы...")
            break

        run_graph_rag_pipeline(query)