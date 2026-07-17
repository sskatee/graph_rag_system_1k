from dataclasses import dataclass
from typing import List


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    vector_score: float = 0.0
    graph_score: float = 0.0
    combined_score: float = 0.0


def adapt_vector(vector_results: list) -> List[Chunk]:
    chunks = []

    # Адаптирую из str в лист (тип аргумента изменён на str)
    # vector_results = vector_results.split('\n')
    # конец

    for index, result in enumerate(vector_results):

        chunk = Chunk(
            id=f"vector_{index}",
            text=result.get("text", ""),
            source=result.get("source", ""),
            vector_score=result.get("score", 0.0)
        )

        chunks.append(chunk)

    return chunks


def adapt_graph(graph_text: str) -> List[Chunk]:

    if not graph_text.strip():
        return []

    return [
        Chunk(
            id="graph_context",
            text=graph_text,
            source="Memgraph",
            graph_score=1.0
        )
    ]


def merge(
    vector_chunks: List[Chunk],
    graph_chunks: List[Chunk]
) -> List[Chunk]:

    chunks = []

    chunks.extend(vector_chunks)
    chunks.extend(graph_chunks)

    for chunk in chunks:
        chunk.combined_score = (
            chunk.vector_score +
            chunk.graph_score
        )

    return chunks


def deduplicate(chunks: List[Chunk]) -> List[Chunk]:

    unique = {}

    for chunk in chunks:
        key = (chunk.source, chunk.text)

        if key not in unique:
            unique[key] = chunk

    return list(unique.values())


def filter_chunks(
    chunks: List[Chunk],
    vector_threshold: float,
    graph_threshold: float,
    vector_force_threshold: float,
    graph_force_threshold: float
) -> List[Chunk]:

    filtered = []

    for chunk in chunks:

        if chunk.vector_score >= vector_force_threshold:
            filtered.append(chunk)
            continue

        if chunk.graph_score >= graph_force_threshold:
            filtered.append(chunk)
            continue

        if (
            chunk.vector_score >= vector_threshold or
            chunk.graph_score >= graph_threshold
        ):
            filtered.append(chunk)

    return filtered


def sort_chunks(chunks: List[Chunk]) -> List[Chunk]:

    return sorted(
        chunks,
        key=lambda chunk: chunk.combined_score,
        reverse=True
    )


def select_until_token_limit(
    chunks: List[Chunk],
    token_limit: int
) -> List[Chunk]:

    selected = []
    current_tokens = 0

    for chunk in chunks:

        tokens = len(chunk.text.split())

        if current_tokens + tokens > token_limit:
            break

        selected.append(chunk)
        current_tokens += tokens

    return selected


def build_context(chunks: List[Chunk]) -> str:

    context_parts = []

    for index, chunk in enumerate(chunks, start=1):

        context_parts.append(
            "\n".join([
                f"[Document {index}]",
                f"Source: {chunk.source}",
                f"Vector score: {chunk.vector_score:.3f}",
                f"Graph score: {chunk.graph_score:.3f}",
                f"Combined score: {chunk.combined_score:.3f}",
                "",
                "Text:",
                chunk.text
            ])
        )

    return "\n\n".join(context_parts)


def build_prompt(
    template: str,
    context: str
) -> str:

    return template.replace("{context}", context)


def build_rag_context(
    vector_results: list,
    graph_text: str,
    token_limit: int = 500,
    vector_threshold: float = 0.5,
    graph_threshold: float = 0.5,
    vector_force_threshold: float = 0.9,
    graph_force_threshold: float = 0.9,
    prompt_template: str = (
        """
    Ты — интеллектуальный ассистент Graph-RAG системы. 
    Отвечай на вопрос пользователя, опираясь СТРОГО на предоставленный контекст из графовой базы знаний.
    Если в контексте нет ответа, честно скажи об этом.
    """
    )
):

    vector_chunks = adapt_vector(vector_results)

    graph_chunks = adapt_graph(graph_text)

    chunks = merge(
        vector_chunks,
        graph_chunks
    )

    chunks = deduplicate(chunks)

    chunks = filter_chunks(
        chunks=chunks,
        vector_threshold=vector_threshold,
        graph_threshold=graph_threshold,
        vector_force_threshold=vector_force_threshold,
        graph_force_threshold=graph_force_threshold
    )

    chunks = sort_chunks(chunks)

    chunks = select_until_token_limit(
        chunks,
        token_limit
    )

    context = build_context(chunks)

    prompt = build_prompt(
        prompt_template,
        context
    )

    return context