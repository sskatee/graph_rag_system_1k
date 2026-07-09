from gqlalchemy import Memgraph

class GraphDB:
    def __init__(self):
        self.db = Memgraph(
            host="3.125.119.243",
            port=7687,
            username="sonorus34@gmail.com",
            password="NewP4ss123",
            encrypted=True
        )

    def init(self):
        self.db.execute_and_fetch("CREATE INDEX ON :Entity(id);")
        self.db.execute_and_fetch(
            "CREATE CONSTRAINT IF NOT EXISTS ON (e:Entity) ASSERT e.id IS UNIQUE;"
        )

    def load_entities(self, entities):
        for e in entities:
            self.db.execute_and_fetch(
                "MERGE (e:Entity {id: $id}) SET e.name = $name, e.type = $type SET e += $props",
                {"id": e["id"], "name": e["name"], "type": e["type"],
                 "props": e.get("properties", {})}
            )

    def load_relationships(self, rels):
        for r in rels:
            self.db.execute_and_fetch(
                "MATCH (a:Entity {id: $src}), (b:Entity {id: $dst}) "
                "MERGE (a)-[r:RELATION {type: $type}]->(b) SET r += $props",
                {"src": r["source"], "dst": r["target"],
                 "type": r["type"], "props": r.get("properties", {})}
            )

    def get_neighbors(self, eid, depth=1):
        return list(self.db.execute_and_fetch(
            f"MATCH (e:Entity {{id: $id}})-[r:RELATION]-(n:Entity) "
            f"WHERE $depth=1 OR (e)-[*..{depth}]-(n) "
            "RETURN DISTINCT n.id AS id, n.name AS name, n.type AS type, "
            "collect(DISTINCT type(r)) AS relations",
            {"id": eid, "depth": depth}
        ))

    def shortest_path(self, start, end, max_depth=4):
        res = list(self.db.execute_and_fetch(
            f"MATCH p = shortestPath((a:Entity {{id: $start}})-[*..{max_depth}]-(b:Entity {{id: $end}})) "
            "RETURN [n IN nodes(p) | {id: n.id, name: n.name, type: n.type}] AS path, "
            "[r IN relationships(p) | type(r)] AS rels",
            {"start": start, "end": end}
        ))
        return res[0] if res else None

    def subgraph(self, ids, depth=1):
        return list(self.db.execute_and_fetch(
            f"MATCH (e:Entity)-[r:RELATION*..{depth}]-(n:Entity) "
            "WHERE e.id IN $ids "
            "RETURN DISTINCT e.id AS src, n.id AS dst, type(r[0]) AS rel_type",
            {"ids": ids}
        ))