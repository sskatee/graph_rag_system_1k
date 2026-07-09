import json
from graph_db import GraphDB

with open ('extracted_graph.json', 'r', encoding='utf8') as f:
    data = json.load(f)

db = GraphDB()
db.init()
db.load_entities(data['entities'])
db.load_relationships((data['relationships']))
print(f'Загружено {len(data["entities"])} узлов и {len(data["relationships"])} связей')
db.close()
