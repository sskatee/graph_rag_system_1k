from gqlalchemy import Memgraph
#from path1 import entities

# Подключение к локальному Memgraph (порт 7687 - стандарт для Bolt протокола)
# Убедись, что твой Memgraph запущен (обычно через Docker: docker run -p 7687:7687 memgraph/memgraph)
memgraph = Memgraph("localhost", 7687)


def find_nodes_in_graph(entities: list[str]) -> list[dict]:
    """
    Этап 2: Mention Matching.
    Ищет узлы в Memgraph по списку сущностей, извлеченных LLM.
    Возвращает список найденных узлов с их внутренними ID для дальнейшего обхода.
    """
    if not entities:
        return []

    # 1. Подготовка данных: дедупликация и приведение к нижнему регистру (слайд 19 и 20)
    # Это спасет от дублей, если LLM вернула ["vLLM", "vllm"]
    unique_entities = list(set(entities))
    lower_entities = [e.lower() for e in unique_entities]

    # 2. Cypher-запрос для поиска узлов
    # Мы ищем узлы, у которых свойство name точно совпадает ИЛИ совпадает без учета регистра.
    # Это базовый уровень "канонизации" и нечеткого поиска.
    query = """
    MATCH (n)
    WHERE n.name IN $entities 
       OR toLower(n.name) IN $lower_entities
    RETURN id(n) AS internal_id, n.name AS canonical_name, labels(n) AS types
    """

    found_nodes = []

    try:
        # 3. Выполнение запроса к Memgraph
        results = memgraph.execute_and_fetch(query, {
            "entities": unique_entities,
            "lower_entities": lower_entities
        })

        # 4. Сборка результатов
        for record in results:
            found_nodes.append({
                "internal_id": record["internal_id"],
                "canonical_name": record["canonical_name"],
                "types": record["types"]  # Например, ['Tool', 'Technology']
            })

        print(f"✅ Найдено в графе: {len(found_nodes)} узлов из {len(unique_entities)} запрошенных.")

    except Exception as e:
        print(f"❌ Ошибка запроса к Memgraph: {e}")

    return found_nodes



# Пример использования (как это запустить)

if __name__ == "__main__":
    #entities -  это то, что вернула нам LLM на Этапе 1
    extracted_entities = ["vLLM", "квантование", "несуществующая_технология"]

    print(f"Ищем сущности: {extracted_entities}")
    nodes = find_nodes_in_graph(extracted_entities)

    for node in nodes:
        print(f" - ID: {node['internal_id']}, Имя: {node['canonical_name']}, Типы: {node['types']}")