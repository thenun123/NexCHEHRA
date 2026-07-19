"""
utils/rag_engine.py — NexCHEHRA RAG (Retrieval-Augmented Generation) Engine
Loads knowledge_base/*.md files, chunks by headings, and answers user questions
using TF-IDF cosine-similarity retrieval + Mistral LLM generation.

Zero external dependencies — uses only Python stdlib + requests (already installed).
"""

import os
import re
import math
import json
import requests
from collections import Counter

from config import MISTRAL_API_KEY, MISTRAL_MODEL, KNOWLEDGE_BASE_DIR

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# ── System prompt for the RAG assistant ──────────────────────────
RAG_SYSTEM_PROMPT = """You are NexBot, the official AI help assistant for the NexCHEHRA platform.
NexCHEHRA is an AI-powered platform that creates virtual influencer videos using a 3-phase pipeline:
- NexBrain™ (AI script & prompt generation)
- NexVision™ (portrait/image generation)
- NexMotion™ (video animation with voice)

RULES:
1. Answer ONLY based on the provided Context. Do not make up information.
2. If the Context does not contain enough information, say: "I don't have specific information about that in my knowledge base. You can try asking about our features, pricing, getting started, or troubleshooting."
3. Be EXTREMELY concise, friendly, and helpful. Start answering directly without unnecessary introductory sentences like "I'd be happy to tell you!". Use emoji sparingly for personality (1 per response max).
4. Keep all responses exceptionally short and punchy. Maximum 2-3 sentences per answer unless the user specifically asks for a detailed list.
5. Do not repeat full lists or paragraphs unless explicitly asked. Summarize the key point quickly.
6. When referencing steps, just state the action efficiently.
7. If the user greets you, respond warmly and suggest what you can help with in one short sentence.
8. NEVER exceed 50-70 words per response. Get straight to the point."""


class NexAssistant:
    """
    Lightweight RAG assistant for NexCHEHRA.
    - Loads .md files from knowledge_base/
    - Chunks by ## headings
    - Uses TF-IDF cosine similarity for retrieval
    - Generates answers via Mistral API
    """

    def __init__(self):
        self.chunks = []       # List of {"title": str, "content": str, "source": str}
        self.tfidf_index = []  # List of term-frequency dicts (one per chunk)
        self.idf = {}          # Inverse document frequency
        self._load_knowledge_base()
        self._build_index()

    # ── Document Loading ─────────────────────────────────────────

    def _load_knowledge_base(self):
        """Read all .md files from the knowledge_base directory and chunk by headings."""
        kb_dir = KNOWLEDGE_BASE_DIR
        if not os.path.isdir(kb_dir):
            print(f"⚠️  Knowledge base directory not found: {kb_dir}")
            return

        for filename in sorted(os.listdir(kb_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(kb_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self._chunk_document(content, filename)

        print(f"[OK] NexBot: Loaded {len(self.chunks)} chunks from {kb_dir}")

    def _chunk_document(self, content: str, source: str):
        """Split a markdown document into chunks by ## or ### headings."""
        # Split by ## or ### (level 2 or 3 headings) while keeping the heading
        sections = re.split(r'\n(?=#{2,3} )', content)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Extract title from first heading line
            lines = section.split('\n', 1)
            title = lines[0].lstrip('#').strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            # Include the title in the content for better search matching
            full_content = f"{title}\n{body}" if body else title

            # Skip very short chunks (likely just a heading with no content)
            if len(full_content.split()) < 5:
                continue

            self.chunks.append({
                "title": title,
                "content": full_content,
                "source": source,
            })

    # ── TF-IDF Indexing ──────────────────────────────────────────

    def _tokenize(self, text: str) -> list:
        """Simple whitespace + punctuation tokenizer with lowercasing and stopword removal."""
        stop_words = {"a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
                      "when", "where", "how", "why", "who", "will", "would", "should", "could",
                      "can", "do", "does", "did", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "for", "with", "about", "against", "between", "into",
                      "through", "during", "before", "after", "above", "below", "to", "from",
                      "up", "down", "in", "out", "on", "off", "over", "under", "again", "further",
                      "then", "once", "here", "there", "all", "any", "both", "each", "few", "more",
                      "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same",
                      "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
                      "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself",
                      "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
                      "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these",
                      "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
                      "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or",
                      "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against",
                      "between", "into", "through", "during", "before", "after", "above", "below", "to",
                      "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further",
                      "then", "once", "please", "can", "tell", "me", "give", "provide", "information", "detail", "details"}
        
        text = text.lower()
        # Remove markdown formatting
        text = re.sub(r'[#*`\[\]()|\-_>!]', ' ', text)
        # Split on non-alphanumeric
        tokens = re.findall(r'[a-z0-9]+', text)
        # Remove stop words and short tokens
        return [t for t in tokens if len(t) > 1 and t not in stop_words]

    def _term_frequency(self, tokens: list) -> dict:
        """Compute normalized term frequency."""
        counts = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {term: count / total for term, count in counts.items()}

    def _build_index(self):
        """Build TF-IDF index over all chunks."""
        if not self.chunks:
            return

        # Compute TF for each chunk
        self.tfidf_index = []
        for chunk in self.chunks:
            tokens = self._tokenize(chunk["content"])
            tf = self._term_frequency(tokens)
            self.tfidf_index.append(tf)

        # Compute IDF across all chunks
        num_docs = len(self.chunks)
        doc_freq = Counter()
        for tf in self.tfidf_index:
            for term in tf:
                doc_freq[term] += 1

        self.idf = {
            term: math.log(num_docs / (1 + df))
            for term, df in doc_freq.items()
        }

    def _cosine_similarity(self, vec_a: dict, vec_b: dict) -> float:
        """Compute cosine similarity between two TF-IDF vectors."""
        # Find common terms
        common = set(vec_a.keys()) & set(vec_b.keys())
        if not common:
            return 0.0

        dot = sum(vec_a[t] * vec_b[t] for t in common)
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)

    # ── Retrieval ────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> list:
        """Find the top_k most relevant chunks for a query."""
        if not self.chunks:
            return []

        # Build query TF-IDF vector
        query_tokens = self._tokenize(query)
        query_tf = self._term_frequency(query_tokens)
        query_tfidf = {
            term: tf * self.idf.get(term, 0)
            for term, tf in query_tf.items()
        }

        # Score each chunk
        scores = []
        for i, chunk_tf in enumerate(self.tfidf_index):
            chunk_tfidf = {
                term: tf * self.idf.get(term, 0)
                for term, tf in chunk_tf.items()
            }
            score = self._cosine_similarity(query_tfidf, chunk_tfidf)
            scores.append((score, i))

        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)

        # Return top_k results (only those with score > 0)
        results = []
        for score, idx in scores[:top_k]:
            if score > 0:
                results.append({
                    **self.chunks[idx],
                    "score": round(score, 4),
                })

        return results

    # ── Generation (RAG) ─────────────────────────────────────────

    def ask(self, query: str) -> str:
        """Full RAG pipeline: retrieve relevant chunks → send to Mistral → return answer."""
        if not MISTRAL_API_KEY:
            return "⚠️ The assistant is not configured. MISTRAL_API_KEY is missing."

        # Step 1: Retrieve relevant context
        results = self.search(query, top_k=3)

        if results:
            context_parts = []
            for r in results:
                context_parts.append(
                    f"[Source: {r['source']}]\n{r['content']}"
                )
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = "No specific information found in the knowledge base for this query."

        # Step 2: Build prompt with context
        user_message = f"""Context from NexCHEHRA Knowledge Base:
---
{context}
---

User Question: {query}

Answer the question based on the context above. If the context doesn't contain relevant information, say so politely."""

        # Step 3: Call Mistral API with lightweight model
        try:
            headers = {
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": MISTRAL_MODEL,
                "temperature": 0.3,
                "max_tokens": 500,
                "messages": [
                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            }

            response = requests.post(
                MISTRAL_API_URL, headers=headers, json=payload, timeout=15
            )
            response.raise_for_status()

            answer = response.json()["choices"][0]["message"]["content"].strip()
            return answer

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 0
            if status_code == 401:
                return "⚠️ The AI assistant's API key is invalid or expired. Please ask the admin to update the MISTRAL_API_KEY in the .env file. You can get a free key at console.mistral.ai"
            elif status_code == 429:
                return "I'm a bit busy right now (rate limit reached). Please wait a few seconds and try again!"
            else:
                return f"Sorry, I'm having trouble connecting (HTTP {status_code}). Please try again in a moment."
        except requests.exceptions.RequestException as e:
            return f"Sorry, I can't reach the AI service right now. Please check your internet connection and try again."
        except (KeyError, IndexError):
            return "Sorry, I received an unexpected response. Please try again."
