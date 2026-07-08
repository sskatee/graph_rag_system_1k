import json
from deepseek import DeepSeekClient


ENTITY_TYPES = [
    "POLITICAL_INSTITUTIONS",              # ПОЛИТИЧЕСКИЕ И ГОСУДАРСТВЕННЫЕ ИНСТИТУТЫ
    "PERSONALITIES",                       # ПЕРСОНАЛИИ
    "POLITICAL_PARTIES_AND_MOVEMENTS",     # ПОЛИТИЧЕСКИЕ ПАРТИИ И ДВИЖЕНИЯ
    "SOCIAL_GROUPS",                       # СОЦИАЛЬНЫЕ ГРУППЫ
    "GEOGRAPHICAL_OBJECTS",                # ГЕОГРАФИЧЕСКИЕ И ТЕРРИТОРИАЛЬНЫЕ ОБЪЕКТЫ
    "DOCUMENTS",                           # ПРАВОВЫЕ И НОРМАТИВНЫЕ ДОКУМЕНТЫ
    "EVENTS",                              # СОБЫТИЯ И ЯВЛЕНИЯ
    "SOCIO-ECONOMIC_PROBLEMS_AND_REFORMS"  # СОЦИАЛЬНО-ЭКОНОМИЧЕСКИЕ ПРОБЛЕМЫ И РЕФОРМЫ
]

RELATION_TYPES = [
    "CAUSED",               # ВЫЗВАЛО (событие → событие) Пример: Индустриализация → возникновение новых социальных групп
    "SIGNED",               # ПОДПИСАЛ (монарх → документ) Пример: Николай II → Манифест 17 октября
    "WAS_IN_FAVOR_OF",      # ВЫСТУПАЛ ЗА (партия / депутат → законопроект) Пример: Трудовики → конфискация помещичьей земли
    "FOUGHT_WITH",          # ВОЕВАЛ С (страна → страна) Пример: Россия → Япония (1904–1905)
    "CONCEDED",             # УСТУПИЛ (страна → территория) Пример: Россия → южный Сахалин (Японии)
    "RENTED",               # АРЕНДОВАЛ (страна → территория) Пример: Россия → Ляодунский полуостров
    "PRECEDED",             # ПРЕДШЕСТВОВАЛО (событие → событие) Пример: I Дума → II Дума
    "PART_OF",              # ВХОДИТ В СОСТАВ (территория → империя) Пример: Финляндия → Российская империя
    "IS_A_TYPE_OF",         # ЯВЛЯЕТСЯ РАЗНОВИДНОСТЬЮ (форма правления → тип монархии) Пример: Дуалистическая монархия → конституционная монархия
    "CHARACTERIZED_AS"      # ХАРАКТЕРИЗУЕТСЯ КАК (событие → атрибут) Пример: II Дума → «Дума народного гнева»
]

print("Ontology:")
print(f"   Entity types:       {ENTITY_TYPES}")
print(f"   Relationship types: {RELATION_TYPES}")


entity_types_str   = ", ".join(ENTITY_TYPES)
relation_types_str = ", ".join(RELATION_TYPES)

with open("text.txt", "r", encoding = "utf-8") as file:
    text = file.read()

prompt_template = f"""
-Goal-
Given documented historical events, identify all entities mentioned in the text and their relationships.

-Allowed Entity Types-
{entity_types_str}

-Allowed Relationship Types-
{relation_types_str}

-Steps-
1. Identify ALL entities. For each entity extract:
   - name: Name of the entity, capitalized
   - type: One of the allowed entity types above
   - description: A brief description of the entity and its role in history based on this text

2. Identify relationships between entities. For each pair extract:
   - source: name of the source entity
   - target: name of the target entity
   - relation: one of the allowed relationship types above
   - description: a sentence explaining why and how these entities are related in this text

-Output Format-
Return a single JSON object with two keys: "entities" and "relationships".
- entities: A list of objects, each with keys: "name", "type", "description".
- relationships: A list of objects, each with keys: "source", "target", "relation", "description".

text: {text}

"""

print(f"\nPreview (first 400 chars):\n{prompt_template[:400]}...")

client = DeepSeekClient(api_key="sk-beb0645699024d40abc08597b1ddb64d")

response = client.chat_completion(
    messages=[
        {"role": "system", "content": "Ты — ассистент, который извлекает сущности и связи из текста в формате JSON."},
        {"role": "user", "content": prompt_template}
    ],
    model = "deepseek-chat",
    response_format = {"type": "json_object"},
    temperature = 0.0,
    max_tokens = 10000
)

result = response.choices[0].message.content
with open("extracted_graph.json", "w", encoding="utf-8") as file:
    try:
        data = json.loads(result)
        json.dump(data, file, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        file.write(result)

print(result)