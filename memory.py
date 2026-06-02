"""
Module de mémoire vectorielle persistante pour l'assistant agentique.
Utilise SQLite pour le stockage et sentence-transformers pour les embeddings.
"""

import os
import json
import sqlite3
import hashlib
import threading
from contextlib import contextmanager

_embedding_model = None
_lock = threading.Lock()


def get_embedding_model():
    """Charge le modèle d'embedding (singleton, lazy-loading)."""
    global _embedding_model
    if _embedding_model is None:
        with _lock:
            if _embedding_model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    _embedding_model = SentenceTransformer(
                        "all-MiniLM-L6-v2",
                        device="cpu",
                    )
                    print("[Memory] Modèle d'embedding chargé (all-MiniLM-L6-v2, CPU)")
                except ImportError:
                    print("[Memory] ERREUR: sentence-transformers non installé. Exécutez 'pip install sentence-transformers'")
                    raise
                except Exception as e:
                    print(f"[Memory] ERREUR lors du chargement du modèle: {e}")
                    raise
    return _embedding_model


class MemoryStore:
    """Stockage de mémoire vectorielle avec recherche par similarité."""

    MAX_CONTENT_TOKENS = 250  # Limite de troncature par résultat

    def __init__(self, db_path=None):
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "memory.db")
        self.db_path = db_path
        self._init_db()
        self._model = None  # lazy

    @property
    def model(self):
        if self._model is None:
            self._model = get_embedding_model()
        return self._model

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    content_hash TEXT UNIQUE,
                    embedding BLOB,
                    category TEXT DEFAULT 'general',
                    importance INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_category ON memories(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_importance ON memories(importance DESC)")

    def _hash_content(self, content):
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _truncate(self, content, max_tokens=None):
        """Tronque le contenu à max_tokens tokens approximatifs (1 token ~ 4 caractères)."""
        if max_tokens is None:
            max_tokens = self.MAX_CONTENT_TOKENS
        max_chars = max_tokens * 4
        if len(content) <= max_chars:
            return content
        return content[:max_chars - 4] + "..."

    def _embed(self, text):
        """Génère l'embedding d'un texte."""
        vec = self.model.encode(text, normalize_embeddings=True)
        return vec.astype("float32").tobytes()

    def remember(self, content, category="general", importance=5):
        """Stocke une information dans la mémoire.

        Args:
            content: L'information textuelle à retenir.
            category: 'preference', 'task', 'contact', 'fact', 'general'
            importance: 1 (faible) à 10 (critique)

        Returns:
            dict avec success/error et l'id du souvenir créé.
        """
        try:
            content = content.strip()
            if not content:
                return {"error": "Contenu vide, rien à mémoriser."}

            content_hash = self._hash_content(content)
            embedding_blob = self._embed(content)

            with self._get_conn() as conn:
                # Vérifier si déjà existant
                existing = conn.execute(
                    "SELECT id FROM memories WHERE content_hash = ?",
                    (content_hash,)
                ).fetchone()

                if existing:
                    # Mettre à jour importance et last_accessed
                    conn.execute(
                        """UPDATE memories
                           SET importance = MAX(importance, ?),
                               last_accessed = CURRENT_TIMESTAMP,
                               access_count = access_count + 1
                           WHERE id = ?""",
                        (importance, existing["id"])
                    )
                    print(f"[Memory] Déjà existant (id={existing['id']}), importance mise à jour.")
                    return {"success": True, "memory_id": existing["id"], "message": "Information déjà connue, importance mise à jour."}

                cursor = conn.execute(
                    """INSERT INTO memories (content, content_hash, embedding, category, importance, last_accessed)
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (content, content_hash, embedding_blob, category, min(max(int(importance), 1), 10))
                )
                mem_id = cursor.lastrowid
                print(f"[Memory] Nouveau souvenir stocké (id={mem_id}, cat={category}, imp={importance})")
                return {"success": True, "memory_id": mem_id, "message": f"Information mémorisée (id={mem_id})."}

        except ImportError:
            return {"error": "Module sentence-transformers non installé. Exécutez 'pip install sentence-transformers'."}
        except Exception as e:
            print(f"[Memory] Erreur remember: {e}")
            return {"error": str(e)}

    def recall(self, query, top_k=3, category=None, min_importance=0):
        """Recherche les souvenirs les plus pertinents.

        Args:
            query: La requête de recherche.
            top_k: Nombre maximum de résultats.
            category: Filtrer par catégorie (optionnel).
            min_importance: Importance minimale (défaut 0 = tout).

        Returns:
            Liste de dicts {id, content, category, importance, similarity, created_at}
        """
        try:
            query_vec = self._embed(query)

            with self._get_conn() as conn:
                if category:
                    rows = conn.execute(
                        """SELECT id, content, category, importance, embedding, created_at
                           FROM memories
                           WHERE category = ? AND importance >= ?
                           ORDER BY importance DESC""",
                        (category, min_importance)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT id, content, category, importance, embedding, created_at
                           FROM memories
                           WHERE importance >= ?
                           ORDER BY importance DESC""",
                        (min_importance,)
                    ).fetchall()

            if not rows:
                return {"results": [], "count": 0}

            import numpy as np
            query_vec_np = np.frombuffer(query_vec, dtype="float32")

            scores = []
            for row in rows:
                emb_bytes = row["embedding"]
                if emb_bytes is None:
                    continue
                db_vec = np.frombuffer(emb_bytes, dtype="float32")
                # Cosine similarity (déjà normalisé, donc dot product)
                similarity = float(np.dot(query_vec_np, db_vec))
                scores.append((similarity, row))

            # Trier par similarité descendante
            scores.sort(key=lambda x: x[0], reverse=True)

            results = []
            for sim, row in scores[:top_k]:
                if sim < 0.2:  # Seuil minimal de pertinence
                    continue
                results.append({
                    "id": row["id"],
                    "content": self._truncate(row["content"]),
                    "category": row["category"],
                    "importance": row["importance"],
                    "similarity": round(sim, 4),
                    "created_at": row["created_at"],
                })

            # Mettre à jour access stats pour les résultats retournés
            if results:
                ids = [r["id"] for r in results]
                with self._get_conn() as conn:
                    conn.executemany(
                        """UPDATE memories
                           SET last_accessed = CURRENT_TIMESTAMP,
                               access_count = access_count + 1
                           WHERE id = ?""",
                        [(rid,) for rid in ids]
                    )

            print(f"[Memory] Rappel: {len(results)} résultats pour '{query[:60]}...'")
            return {"results": results, "count": len(results)}

        except ImportError:
            return {"error": "Module sentence-transformers non installé."}
        except Exception as e:
            print(f"[Memory] Erreur recall: {e}")
            return {"error": str(e)}

    def forget(self, memory_id):
        """Supprime un souvenir par son ID.

        Args:
            memory_id: L'ID du souvenir à supprimer.

        Returns:
            dict avec success ou error.
        """
        try:
            memory_id = int(memory_id)
            with self._get_conn() as conn:
                cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                if cursor.rowcount == 0:
                    return {"error": f"Souvenir id={memory_id} non trouvé."}
                print(f"[Memory] Souvenir supprimé (id={memory_id})")
                return {"success": True, "message": f"Souvenir {memory_id} supprimé."}
        except Exception as e:
            print(f"[Memory] Erreur forget: {e}")
            return {"error": str(e)}

    def get_stats(self):
        """Retourne des statistiques sur la mémoire."""
        try:
            with self._get_conn() as conn:
                total = conn.execute("SELECT COUNT(*) as cnt FROM memories").fetchone()["cnt"]
                by_cat = conn.execute(
                    "SELECT category, COUNT(*) as cnt FROM memories GROUP BY category"
                ).fetchall()
                categories = {row["category"]: row["cnt"] for row in by_cat}
                return {
                    "total_memories": total,
                    "by_category": categories,
                }
        except Exception as e:
            return {"error": str(e)}