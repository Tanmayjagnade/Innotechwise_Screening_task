import glob
import os
from typing import List

from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

CORPUS_DIR = "data/corpus"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "epr_docs"
TOP_K = 4

_collection = None


def init_rag() -> None:
    global _collection

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    _collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)

    if _collection.count() == 0:
        _index_corpus()


def _chunk_text(text: str, chunk_words: int = 120, overlap: int = 20) -> List[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_words])
        if chunk.strip():
            chunks.append(chunk.strip())
        i += chunk_words - overlap
    return chunks


def _index_corpus() -> None:
    ids, docs, metas = [], [], []

    for filepath in sorted(glob.glob(f"{CORPUS_DIR}/*.txt")):
        filename = os.path.basename(filepath)
        with open(filepath, encoding="utf-8") as f:
            raw = f.read()

        # Split on section headers (lines starting with #)
        current_section = "General"
        buffer: List[str] = []

        def flush(section: str, buf: List[str], file: str) -> None:
            text = " ".join(buf).strip()
            if not text:
                return
            for j, chunk in enumerate(_chunk_text(text)):
                chunk_id = f"{file}__{section.replace(' ', '_')[:40]}__{j}"
                ids.append(chunk_id)
                docs.append(chunk)
                metas.append({"source": file, "section": section})

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                flush(current_section, buffer, filename)
                buffer = []
                current_section = stripped.lstrip("#").strip()
            else:
                buffer.append(stripped)

        flush(current_section, buffer, filename)

    if ids:
        _collection.add(documents=docs, ids=ids, metadatas=metas)


def _dedupe_citations(metas: List[dict]) -> List[dict]:
    seen, out = set(), []
    for m in metas:
        key = (m["source"], m["section"])
        if key not in seen:
            seen.add(key)
            label = m["source"].replace(".txt", "").replace("_", " ").title()
            out.append({"document": label, "section": m["section"]})
    return out


def answer_question(question: str) -> dict:
    results = _collection.query(query_texts=[question], n_results=TOP_K)

    retrieved_docs: List[str] = results["documents"][0]
    retrieved_metas: List[dict] = results["metadatas"][0]

    if not retrieved_docs:
        return {
            "answer": "I do not know based on the provided documents.",
            "citations": [],
        }

    context_blocks = []
    for doc, meta in zip(retrieved_docs, retrieved_metas):
        label = meta["source"].replace(".txt", "").replace("_", " ").title()
        context_blocks.append(f"[{label} — {meta['section']}]\n{doc}")

    context = "\n\n---\n\n".join(context_blocks)

    prompt = (
        f"Use the following excerpts to answer the question. "
        f"Only use information from the excerpts. "
        f"If the excerpts do not contain the answer, say: UNKNOWN\n\n"
        f"Excerpts:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer (based only on excerpts above):"
    )

    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    message = client.chat.completions.create(
        model="llama3.2:1b",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = message.choices[0].message.content.strip()

    if "unknown" in answer.lower() or len(answer) < 10:
        return {
            "answer": "I do not know based on the provided documents.",
            "citations": [],
        }

    citations = _dedupe_citations(retrieved_metas)
    return {"answer": answer, "citations": citations}
