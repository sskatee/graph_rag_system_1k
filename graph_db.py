from neo4j import GraphDatabase


class GraphDB:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("memgraph", "memgraph")
        )

    def init(self):
        """Создаёт индексы."""
        with self.driver.session() as session:
            try:
                session.run("CREATE INDEX ON :Entity(id);")
                session.run("CREATE INDEX ON :Entity(name);")
                print("   ✅ Индексы созданы")
            except Exception as e:
                print(f"   ⚠️ Ошибка при создании индексов: {e}")

    def remove_duplicate_entities(self):
        """
        Удаляет дубликаты сущностей с одинаковым именем (name),
        оставляя только один узел. Связи переносятся на оставшийся узел
        перед удалением дубликата.
        """
        with self.driver.session() as session:
            # Находим все дубликаты по имени (без учёта регистра)
            result = session.run(
                "MATCH (e:Entity) "
                "WITH toLower(e.name) AS lower_name, collect(e) AS nodes, count(*) AS cnt "
                "WHERE cnt > 1 "
                "RETURN lower_name, nodes, cnt "
                "ORDER BY cnt DESC"
            )

            duplicates = list(result)

            if not duplicates:
                print("✅ Дубликатов не найдено.")
                return

            total_removed = 0

            for record in duplicates:
                nodes = record["nodes"]
                # Оставляем первый узел, остальные — дубликаты
                keep_node = nodes[0]
                duplicate_nodes = nodes[1:]

                for dup_node in duplicate_nodes:
                    try:
                        # Переносим связи с дубликата на основной узел
                        session.run(
                            "MATCH (dup:Entity) WHERE id(dup) = $dup_id "
                            "MATCH (keep:Entity) WHERE id(keep) = $keep_id "
                            "MATCH (dup)-[r:RELATION]-(other:Entity) "
                            "WHERE other <> keep "
                            "MERGE (keep)-[new_r:RELATION {type: type(r), "
                            "description: r.description, chunk_id: r.chunk_id}]->(other) "
                            "SET new_r = properties(r)",
                            {"dup_id": dup_node.id, "keep_id": keep_node.id}
                        )

                        # Удаляем дубликат
                        session.run(
                            "MATCH (e:Entity) WHERE id(e) = $dup_id "
                            "DETACH DELETE e",
                            {"dup_id": dup_node.id}
                        )

                        total_removed += 1

                    except Exception as ex:
                        print(f"   ⚠️ Ошибка при удалении дубликата "
                              f"{dup_node.get('name', 'unknown')}: {ex}")

            print(f"✅ Удалено дубликатов: {total_removed}")

            # Проверяем результат
    def load_entities(self, entities):
        """Загружает сущности."""
        print("   Загрузка сущностей...")
        with self.driver.session() as session:
            for e in entities:
                try:
                    session.run(
                        "CREATE (e:Entity {id: $id, name: $name, type: $type, description: $desc})",
                        {
                            "id": e["name"],
                            "name": e["name"],
                            "type": e.get("type", "Unknown"),
                            "desc": e.get("description", "")
                        }
                    )
                except Exception as ex:
                    print(f"   ⚠️ Ошибка при создании {e['name']}: {ex}")

            # Проверяем результат
            result = session.run("MATCH (e:Entity) RETURN count(e) AS cnt")
            count = result.single()["cnt"]
            print(f"   ✅ Загружено {count} сущностей")

    def load_relationships(self, rels):
        """Загружает связи."""
        print("   Загрузка связей...")
        with self.driver.session() as session:
            loaded = 0
            for r in rels:
                try:
                    result = session.run(
                        "MATCH (a:Entity {id: $src}), (b:Entity {id: $dst}) "
                        "CREATE (a)-[:RELATION {type: $rel, description: $desc, chunk_id: $chunk_id}]->(b) "
                        "RETURN a.id AS src, b.id AS dst",
                        {
                            "src": r["source"],
                            "dst": r["target"],
                            "rel": r.get("relation", "RELATED_TO"),
                            "desc": r.get("description", ""),
                            "chunk_id": r.get("chunk id", 0)
                        }
                    )
                    if result.single():
                        loaded += 1
                except Exception as ex:
                    print(f"   ⚠️ Ошибка связи {r.get('source')}->{r.get('target')}: {ex}")

            print(f"   ✅ Загружено {loaded} из {len(rels)} связей")

    def find_nodes_by_names(self, names):
        """Ищет узлы по списку имён."""
        if not names:
            return []
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n:Entity) WHERE n.id IN $names "
                "RETURN id(n) AS internal_id, n.id AS canonical_name, labels(n) AS types",
                {"names": list(set(names))}
            )
            return [dict(record) for record in result]

    def get_neighbors(self, eid, depth=1):
        """Возвращает соседей сущности."""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (e:Entity {id: $id})-[r:RELATION]-(n:Entity) "
                "RETURN DISTINCT id(n) AS internal_id, n.id AS entity_id, "
                "n.name AS name, n.type AS type, "
                "collect(DISTINCT type(r)) AS relations",
                {"id": eid}
            )
            return [dict(record) for record in result]

    def shortest_path(self, start, end, max_depth=4):
        """Кратчайший путь между двумя entity id."""
        with self.driver.session() as session:
            result = session.run(
                f"MATCH p = shortestPath((a:Entity {{id: $start}})-[*..{max_depth}]-(b:Entity {{id: $end}})) "
                "RETURN [n IN nodes(p) | {id: n.id, name: n.name, type: n.type}] AS path, "
                "[r IN relationships(p) | type(r)] AS rels",
                {"start": start, "end": end}
            )
            record = result.single()
            return dict(record) if record else None

    def subgraph(self, ids, depth=1):
        """Извлекает подграф вокруг списка entity id."""
        with self.driver.session() as session:
            result = session.run(
                f"MATCH (e:Entity)-[r:RELATION*..{depth}]-(n:Entity) "
                "WHERE e.id IN $ids "
                "RETURN DISTINCT e.id AS src, n.id AS dst, type(r[0]) AS rel_type",
                {"ids": ids}
            )
            return [dict(record) for record in result]

    def close(self):
        """Закрывает соединение с базой данных."""
        if hasattr(self.driver, 'close'):
            self.driver.close()