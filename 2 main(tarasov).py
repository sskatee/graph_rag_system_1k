import json
from deepseek import DeepSeekClient
import pymorphy3

# Задаем типы сущностей и отношений, которые содержатся в конспектах по истории
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

# Запишем все сущности и отношения в строки, чтобы использовать их в тексте промта
entity_types_str   = ", ".join(ENTITY_TYPES)
relation_types_str = ", ".join(RELATION_TYPES)

# Считываем файл с обработанными чанками
file_path = "documents/chunks_list.json"
with open(file_path, 'r', encoding='utf-8') as file1:
    f = json.load(file1)

# Создадим словарь сущностей и отношений. Туда мы будем записывать их после каждой обработки запроса Дипсиком. В дальнейшем мы загрузим этот словарь в файл.
ontology = {"entities" : [], "relationships" : []}
entities_names = set()
relationships_names = set()

k = 0
for chunk in f:
    k += 1 # Номер чанка

    # Текст промта для ИИ
    prompt_template = f"""
    -Goal-
    Given documented historical events, identify all entities mentioned in the chunks and their relationships.
    
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
       - description: a sentence explaining why and how these entities are related in this chunk
       - chunk id: {k} 
    
    -Output Format-
    Return a single JSON object with two keys: "entities" and "relationships".
    - entities: A list of objects, each with keys: "name", "type", "description".
    - relationships: A list of objects, each with keys: "source", "target", "relation", "description", "chunk id".
    
    сhunk: {chunk}
    
    """

    client = DeepSeekClient(api_key="sk-beb0645699024d40abc08597b1ddb64d")

    # Пишем запрос Дипсику
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

    # Берем JSON-файл, который выдал нам Дипсик, считываем сущности и отношения из него и добавляем их в словарь
    result = response.choices[0].message.content
    data = json.loads(result)
    for x in data["entities"]:
        morph = pymorphy3.MorphAnalyzer()
        # Анализ слова. parse() возвращает список возможных вариантов разбора.
        parses = morph.parse(x["name"])
        # Выбираем первый (самый вероятный) вариант и берем его нормальную форму
        normal_form = parses[0].normal_form
        if normal_form not in entities_names:
            ontology["entities"].append(x)
            entities_names.add(normal_form)
    for x in data["relationships"]:
        ontology["relationships"].append(x)

# Записываем словарь сущностей и отношений в файл
with open("extracted_graph.json", "w", encoding="utf-8") as file2:
    try:
        json.dump(ontology, file2, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        print("ERROR")

