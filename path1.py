import os
import json
import re
from openai import OpenAI

# Инициализация клиента DeepSeek (из llm-deepseek.py)
os.environ['DEEPSEEK_API_KEY'] = 'sk-beb0645699024d40abc08597b1ddb64d'
client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

MODEL_NAME = "deepseek-v4-pro"  # Укажи имя модели, которое ты загрузил в vLLM


def extract_entities(query: str) -> list[str]:
    """
    Отправляет запрос пользователя в LLM (vLLM) для извлечения ключевых сущностей.
    Возвращает список канонических названий сущностей.
    """

    # 1. Формируем системный промпт (роль system, см. слайд 4)
    # Мы жестко требуем от модели вернуть ТОЛЬКО JSON-массив, без лишнего текста.
    system_prompt = """
    Ты — система извлечения сущностей для графовой базы данных.
    Твоя задача: проанализировать запрос пользователя и извлечь из него ключевые сущности 
    (технологии, названия инструментов, концепции, имена собственные).

    ПРАВИЛА:
    1. Верни результат СТРОГО в формате JSON-массива строк. 
    2. Не добавляй никаких пояснений, текста до или после JSON.
    3. Если сущностей нет, верни пустой массив [].
    4. Приводи сущности к каноническому виду (например, "видеокарта" -> "GPU").
    5. Сущности начинай СТРОГО С ЗАГЛАВНОЙ БУКВЫ!

    ПРИМЕР:
    Запрос: "Как vLLM использует видеокарту и какие форматы квантования поддерживает?"
    Ответ: ["vLLM", "GPU", "Квантование"]
    """

    # 2. Делаем асинхронный HTTP-запрос к vLLM (слайд 5)
    try:
        # Вызов DeepSeek через библиотеку openai
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1,  # Низкая температура для детерминированного ответа
            stream=False
        )

        # Достаем текст ответа
        raw_content = response.choices[0].message.content

        # Парсим JSON из ответа
        entities = parse_json_from_llm(raw_content)

        print(f"Извлечено сущностей: {len(entities)}")
        return entities

    except Exception as e:
        print(f"Ошибка при вызове DeepSeek: {e}")
        return []


def parse_json_from_llm(raw_text: str) -> list[str]:
    """
    Вспомогательная функция для безопасного парсинга JSON.
    LLM часто оборачивает JSON в markdown-блоки (```json ... ```),
    этот код их аккуратно срезает.
    """
    # Ищем массив в тексте с помощью регулярного выражения
    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Если парсинг не удался, возвращаем пустой список (или можно сделать fallback)
    print(f"Не удалось распарсить JSON из ответа LLM: {raw_text}")
    return []



# Пример использования (как это запустить)
if __name__ == "__main__":
    # Тестовые запросы
    test_queries = [
        "Как vLLM использует GPU и какие форматы квантования поддерживает?",
        "Расскажи про Qdrant и Memgraph",
        "Что такое эмбеддинги?"
    ]

    for query in test_queries:
        print(f"\n Запрос: {query}")
        entities = extract_entities(query)
        print(f" Сущности: {entities}")