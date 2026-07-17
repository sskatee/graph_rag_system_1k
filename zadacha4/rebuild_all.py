# rebuild_all.py
from chunk_indexer import index_chunks
from entity_indexer import index_entities

if __name__ == "__main__":
    print("=" * 50)
    print("ПЕРЕСТРОЙКА ВСЕХ ИНДЕКСОВ")
    print("=" * 50)

    print("\n1. Индексация чанков...")
    index_chunks()

    print("\n2. Индексация сущностей...")
    index_entities()

    print("\n" + "=" * 50)
    print("ГОТОВО. Все индексы обновлены.")
    print("=" * 50)