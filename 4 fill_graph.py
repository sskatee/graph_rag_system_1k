import json
from graph_db import GraphDB

with open('extracted_graph.json', 'r', encoding='utf8') as f:
    data = json.load(f)

print(f"📄 В файле: {len(data['entities'])} сущностей, {len(data['relationships'])} связей")

db = GraphDB()
db.init()
db.load_entities(data['entities'])
db.load_relationships(data['relationships'])
print("Проверка загруженных данных...")
with db.driver.session() as session:
    # Проверяем сущности
    result = session.run("MATCH (e:Entity) RETURN count(e) AS cnt")
    count = result.single()["cnt"]
    print(f"   📊 В БД {count} сущностей")

    if count > 0:
        result = session.run("MATCH (e:Entity) RETURN e.id, e.name, e.type LIMIT 5")
        print("   📝 Примеры сущностей:")
        for record in result:
            print(f"      - ID: '{record['e.id']}', Name: '{record['e.name']}', Type: {record['e.type']}")

    # Проверяем связи
    result = session.run("MATCH ()-[r:RELATION]->() RETURN count(r) AS cnt")
    count = result.single()["cnt"]
    print(f"   📊 В БД {count} связей")

    if count > 0:
        result = session.run("MATCH (a)-[r:RELATION]->(b) RETURN a.id AS src, b.id AS dst, type(r) AS rel LIMIT 3")
        print("   📝 Примеры связей:")
        for record in result:
            print(f"      - {record['src']} -> {record['rel']} -> {record['dst']}")

db.close()