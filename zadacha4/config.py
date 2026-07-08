import os

# vLLM Embedding сервер
VLLM_EMBED_BASE_URL = "http://localhost:8001/v1"
VLLM_EMBED_MODEL = "google/embeddinggemma-300m"
VLLM_EMBED_API_KEY = "not-needed"

# Qdrant
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_CHUNKS_COLLECTION = "chunks"
QDRANT_ENTITIES_COLLECTION = "entities"
VECTOR_DIM = 768

# Memgraph
MEMGRAPH_URI = "bolt://localhost:7687"

# Пути
CHUNKS_INPUT_FILE = "../task1_data_processing/chunks.jsonl"  # от задачи №1