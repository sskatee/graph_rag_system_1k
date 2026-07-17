'''
from openai import OpenAI
from config import VLLM_EMBED_BASE_URL, VLLM_EMBED_MODEL, VLLM_EMBED_API_KEY

# Клиент к vLLM (использует OpenAI-совместимый API)
client = OpenAI(
    base_url=VLLM_EMBED_BASE_URL,
    api_key=VLLM_EMBED_API_KEY
)


def get_embeddings(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Получает эмбеддинги для списка текстов.
    vLLM принимает массив строк, но лучше отправлять батчами по 32.
    Возвращает список векторов в том же порядке.
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            model=VLLM_EMBED_MODEL,
            input=batch
        )
        # Сортируем по индексу, чтобы порядок гарантированно сохранился
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_embeddings.extend([item.embedding for item in sorted_data])
        print(f"  Векторизовано {min(i + batch_size, len(texts))}/{len(texts)}")

    return all_embeddings


def get_single_embedding(text: str) -> list[float]:
    """Эмбеддинг для одного текста (используется в поиске)."""
    return get_embeddings([text])[0]
'''
from sentence_transformers import SentenceTransformer

# Загружаем модель один раз при старте
model = SentenceTransformer('intfloat/multilingual-e5-base')

def get_embeddings(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Получает эмбеддинги для списка текстов.
    sentence-transformers сам обрабатывает батчи эффективно.
    """
    # Модель возвращает numpy-массив, преобразуем в list
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True)
    return embeddings.tolist()


def get_single_embedding(text: str) -> list[float]:
    """Эмбеддинг для одного текста."""
    return get_embeddings([text])[0]