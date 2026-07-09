from gqlalchemy import Memgraph

class GraphDB:
    def __init__(self):
        self.db = Memgraph(
            host="localhost",
            port=7687,
            username="memgraph",
            password="memgraph",
            encrypted=False
        )

    def init(self):
        """Создаёт индекс и constraint для уникальности id."""
        self.db.execute_and_fetch("CREATE INDEX ON :Entity(id);")
        self.db.execute_and_fetch(
            "CREATE CONSTRAINT IF NOT EXISTS ON (e:Entity) ASSERT e.id IS UNIQUE;"
        )

    def load_entities(self, entities):
        """Загружает сущности. Теперь сохраняет description."""
        for e in entities:
            self.db.execute_and_fetch(
                "MERGE (e:Entity {id: $id}) "
                "SET e.name = $name, e.type = $type, e.description = $desc "
                "SET e += $props",
                {
                    "id": e["id"],
                    "name": e["name"],
                    "type": e["type"],
                    "desc": e.get("description", ""),
                    "props": e.get("properties", {})
                }
            )

    def load_relationships(self, rels):
        """Загружает связи."""
        for r in rels:
            self.db.execute_and_fetch(
                "MATCH (a:Entity {id: $src}), (b:Entity {id: $dst}) "
                "MERGE (a)-[r:RELATION {type: $type}]->(b) SET r += $props",
                {
                    "src": r["source"],
                    "dst": r["target"],
                    "type": r["type"],
                    "props": r.get("properties", {})
                }
            )

    def find_nodes_by_names(self, names):
        """
        Ищет узлы по списку имён (для path2.py).
        Возвращает список словарей с internal_id, canonical_name, types.
        """
        if not names:
            return []
        unique_names = list(set(names))
        lower_names = [n.lower() for n in unique_names]
        result = self.db.execute_and_fetch(
            "MATCH (n) WHERE n.name IN $names OR toLower(n.name) IN $lower "
            "RETURN id(n) AS internal_id, n.name AS canonical_name, labels(n) AS types",
            {"names": unique_names, "lower": lower_names}
        )
        return list(result)

    def get_neighbors(self, eid, depth=1):
        """
        Возвращает соседей сущности по её entity id (строковому).
        Теперь отдаёт internal_id узла (нужно для path3).
        """
        return list(self.db.execute_and_fetch(
            f"MATCH (e:Entity {{id: $id}})-[r:RELATION]-(n:Entity) "
            f"WHERE $depth=1 OR (e)-[*..{depth}]-(n) "
            "RETURN DISTINCT id(n) AS internal_id, n.id AS entity_id, "
            "n.name AS name, n.type AS type, "
            "collect(DISTINCT type(r)) AS relations",
            {"id": eid, "depth": depth}
        ))

    def shortest_path(self, start, end, max_depth=4):
        """Кратчайший путь между двумя entity id."""
        res = list(self.db.execute_and_fetch(
            f"MATCH p = shortestPath((a:Entity {{id: $start}})-[*..{max_depth}]-(b:Entity {{id: $end}})) "
            "RETURN [n IN nodes(p) | {id: n.id, name: n.name, type: n.type}] AS path, "
            "[r IN relationships(p) | type(r)] AS rels",
            {"start": start, "end": end}
        ))
        return res[0] if res else None

    def subgraph(self, ids, depth=1):
        """Извлекает подграф вокруг списка entity id."""
        return list(self.db.execute_and_fetch(
            f"MATCH (e:Entity)-[r:RELATION*..{depth}]-(n:Entity) "
            "WHERE e.id IN $ids "
            "RETURN DISTINCT e.id AS src, n.id AS dst, type(r[0]) AS rel_type",
            {"ids": ids}
        ))
