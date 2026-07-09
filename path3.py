from gqlalchemy import Memgraph
from typing import Dict, List, Tuple

# Подключение к Memgraph
memgraph = Memgraph("localhost", 7687)


def get_neighbors(node_ids: List[int], max_depth: int = 1) -> Dict[str, List]:
    """
    Поиск соседей: находит все узлы, связанные с заданными узлами.

    Args:
        node_ids: Внутренние ID узлов из Этапа 2
        max_depth: Глубина обхода (1 = прямые соседи, 2 = соседи соседей)

    Returns:
        Словарь с узлами и ребрами
    """
    if not node_ids:
        return {"nodes": [], "edges": []}

    # Cypher-запрос для поиска соседей
    # Мы ищем все узлы, которые связаны с нашими узлами через любые отношения
    query = f"""
    MATCH (start)-[r*1..{max_depth}]-(neighbor)
    WHERE id(start) IN $node_ids
    RETURN DISTINCT 
        id(start) AS start_id, 
        start.name AS start_name,
        labels(start) AS start_labels,
        type(r[0]) AS relation_type,
        id(neighbor) AS neighbor_id,
        neighbor.name AS neighbor_name,
        labels(neighbor) AS neighbor_labels,
        r[0].evidence AS evidence,
        id(r[0]) AS edge_id
    """

    nodes_dict = {}
    edges_set = set()  # Для дедупликации рёбер по ID
    edges_list = []

    try:
        results = memgraph.execute_and_fetch(query, {"node_ids": node_ids})

        for record in results:
            # Добавляем начальный узел
            start_id = record["start_id"]
            if start_id not in nodes_dict:
                nodes_dict[start_id] = {
                    "id": start_id,
                    "name": record["start_name"],
                    "labels": record["start_labels"]
                }

            # Добавляем соседний узел
            neighbor_id = record["neighbor_id"]
            if neighbor_id not in nodes_dict:
                nodes_dict[neighbor_id] = {
                    "id": neighbor_id,
                    "name": record["neighbor_name"],
                    "labels": record["neighbor_labels"]
                }

            # Дедупликация рёбер по ID ребра (уникальный в графе)
            edge_id = record.get("edge_id")
            if edge_id is not None and edge_id not in edges_set:
                edges_set.add(edge_id)
                # Добавляем ребро
                edges_list.append({
                    "from": start_id,
                    "to": neighbor_id,
                    "relation": record["relation_type"],
                    "evidence": record.get("evidence", "unknown")
                })

        print(f"✅ Найдено соседей: {len(nodes_dict)} узлов, {len(edges_list)} связей")

    except Exception as e:
        print(f"❌ Ошибка поиска соседей: {e}")

    return {
        "nodes": list(nodes_dict.values()),
        "edges": edges_list
    }


def get_shortest_paths(entity_pairs: List[Tuple[int, int]], max_path_length: int = 5) -> Dict[str, List]:
    """
    Поиск кратчайших путей между парами сущностей.

    Args:
        entity_pairs: Список пар (id1, id2) между которыми ищем путь
        max_path_length: Максимальная длина пути (ограничение, чтобы не уйти в бесконечность)

    Returns:
        Словарь с узлами и ребрами всех найденных путей
    """
    if not entity_pairs:
        return {"nodes": [], "edges": []}

    nodes_dict = {}
    edges_list = []

    for node1_id, node2_id in entity_pairs:
        # Cypher-запрос для поиска кратчайшего пути
        query = f"""
        MATCH p = (n1)-[*1..{max_path_length}]-(n2)
        WHERE id(n1) = $node1_id AND id(n2) = $node2_id
        WITH p
        ORDER BY length(p)
        LIMIT 1
        RETURN 
            nodes(p) AS path_nodes,
            [r IN relationships(p) | {{
                id: id(r),
                type: type(r),
                from_id: id(startNode(r)),
                to_id: id(endNode(r)),
                evidence: r.evidence
            }}] AS path_edges
        """

        try:
            results = memgraph.execute_and_fetch(query, {
                "node1_id": node1_id,
                "node2_id": node2_id
            })

            for record in results:
                # Обрабатываем узлы
                for node in record["path_nodes"]:
                    node_id = node.id
                    if node_id not in nodes_dict:
                        node_name = node.properties.get('name', 'unknown') if hasattr(node,
                                                                                      'properties') and isinstance(
                            node.properties, dict) else getattr(node, 'name', 'unknown')
                        node_labels = list(node.labels) if hasattr(node, 'labels') else []

                        nodes_dict[node_id] = {
                            "id": node_id,
                            "name": node_name,
                            "labels": node_labels
                        }

                # Добавляем все рёбра из пути
                for edge_dict in record["path_edges"]:
                    edges_list.append({
                        "from": edge_dict["from_id"],
                        "to": edge_dict["to_id"],
                        "relation": edge_dict["type"],
                        "evidence": edge_dict.get("evidence", "unknown")
                    })

        except Exception as e:
            print(f"❌ Ошибка поиска пути между {node1_id} и {node2_id}: {e}")

    print(f"✅ Найдено путей: {len(entity_pairs)} пар, {len(nodes_dict)} узлов, {len(edges_list)} связей")

    return {
        "nodes": list(nodes_dict.values()),
        "edges": edges_list
    }


def build_subgraph(
        found_nodes: List[Dict],
        neighbor_depth: int = 1,
        find_paths_between: bool = True
) -> Dict[str, List]:
    """
    Главная функция: собирает подграф релевантных отношений.

    Args:
        found_nodes: Список узлов из Этапа 2 (с internal_id)
        neighbor_depth: Глубина поиска соседей
        find_paths_between: Искать ли пути между всеми парами сущностей

    Returns:
        Единый подграф со всеми узлами и ребрами
    """
    if not found_nodes:
        return {"nodes": [], "edges": []}

    # Извлекаем ID найденных узлов
    node_ids = [node["internal_id"] for node in found_nodes]

    # 1. Поиск соседей
    neighbors_result = get_neighbors(node_ids, max_depth=neighbor_depth)

    # 2. Поиск кратчайших путей между всеми парами
    paths_result = {"nodes": [], "edges": []}
    if find_paths_between and len(node_ids) > 1:
        entity_pairs = []
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                entity_pairs.append((node_ids[i], node_ids[j]))

        paths_result = get_shortest_paths(entity_pairs)

    # 3. Объединяем результаты (с дедупликацией)
    all_nodes = {}
    all_edges = {}

    for node in neighbors_result["nodes"]:
        all_nodes[node["id"]] = node

    for node in paths_result["nodes"]:
        all_nodes[node["id"]] = node

    for edge in neighbors_result["edges"]:
        edge_key = (edge["from"], edge["to"], edge["relation"])
        all_edges[edge_key] = edge

    for edge in paths_result["edges"]:
        if edge["from"] is not None and edge["to"] is not None:
            edge_key = (edge["from"], edge["to"], edge["relation"])
            all_edges[edge_key] = edge

    final_subgraph = {
        "nodes": list(all_nodes.values()),
        "edges": list(all_edges.values())
    }

    print(f"🎯 Итоговый подграф: {len(final_subgraph['nodes'])} узлов, {len(final_subgraph['edges'])} связей")

    return final_subgraph


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
# Пример использования
# ==========================================
if __name__ == "__main__":
    found_nodes = [
        {"internal_id": 0, "canonical_name": "vLLM", "labels": ["Tool"]},
        {"internal_id": 4, "canonical_name": "квантование", "labels": ["Concept"]}
    ]

    print("Строим подграф...")
    subgraph = build_subgraph(
        found_nodes=found_nodes,
        neighbor_depth=1,
        find_paths_between=True
    )

    print("\nУзлы:")
    for node in subgraph["nodes"]:
        print(f"  - {node['name']} (ID: {node['id']}, метки: {node['labels']})")

    print("\nСвязи:")
    for edge in subgraph["edges"]:
        print(f"  - {edge['from']} --[{edge['relation']}]--> {edge['to']} (источник: {edge['evidence']})")
