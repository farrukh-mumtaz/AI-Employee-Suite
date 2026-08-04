# Tests for backend/app/core/retrieval.py's dialect-aware document
# retrieval -- the shared RAG layer the Support Agent's
# retrieve_refund_policy_node depends on (via core/rag_node.py).
#
# Bug fixed: retrieve_relevant_docs() unconditionally used
# Document.embedding.cosine_distance(...), which compiles to pgvector's
# `<=>` operator -- valid only on Postgres. Running it against SQLite (this
# project's local DATABASE_URL) raised
# `sqlite3.OperationalError: near ">": syntax error`, and since this used to
# run as a bare module-level statement in test_rag.py, it crashed pytest's
# *collection* phase for the whole repo, not just one test -- see
# test_rag.py's updated docstring/comment.
#
# retrieve_relevant_docs() now detects the engine dialect: Postgres keeps
# the real pgvector query (verified below without needing a live Postgres
# server, by asserting the constructed SQL); every other dialect (SQLite
# here) falls back to computing cosine similarity in Python.
#
# Run with: python -m pytest test_retrieval.py -v
import unittest
from unittest.mock import MagicMock, patch

from backend.app.core import retrieval


class CosineSimilarityTests(unittest.TestCase):
    """Unit tests for the pure-Python helper backing the SQLite fallback."""

    def test_identical_vectors_have_similarity_one(self):
        self.assertAlmostEqual(retrieval._cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_orthogonal_vectors_have_similarity_zero(self):
        self.assertAlmostEqual(retrieval._cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_opposite_vectors_have_similarity_negative_one(self):
        self.assertAlmostEqual(retrieval._cosine_similarity([1.0, 0.0], [-1.0, 0.0]), -1.0)

    def test_zero_vector_returns_zero_instead_of_dividing_by_zero(self):
        self.assertEqual(retrieval._cosine_similarity([0.0, 0.0], [1.0, 1.0]), 0.0)


class RetrieveRelevantDocsSQLiteFallbackTests(unittest.TestCase):
    """Regression coverage for the exact bug: querying against this
    project's real (SQLite) engine must not raise, unlike before the fix."""

    def test_current_local_engine_is_sqlite(self):
        # Sanity check that this suite is actually exercising the fallback
        # path it claims to -- if DATABASE_URL ever changes to Postgres,
        # this test (not a silent false-pass) is what will flag it.
        self.assertEqual(retrieval.engine.dialect.name, "sqlite")

    @patch.object(retrieval, "embed_text", return_value=[1.0, 0.0, 0.0])
    def test_query_against_sqlite_does_not_raise(self, mock_embed_text):
        # Before the fix, this raised sqlalchemy.exc.OperationalError.
        results = retrieval.retrieve_relevant_docs("any query", top_k=3)
        self.assertIsInstance(results, list)

    @patch.object(retrieval, "embed_text", return_value=[1.0, 0.0, 0.0])
    def test_ranks_documents_by_cosine_similarity_most_relevant_first(self, mock_embed_text):
        near = MagicMock(content="near", embedding=[0.9, 0.1, 0.0])
        far = MagicMock(content="far", embedding=[0.0, 1.0, 0.0])
        opposite = MagicMock(content="opposite", embedding=[-1.0, 0.0, 0.0])

        fake_session = MagicMock()
        fake_session.exec.return_value.all.return_value = [far, opposite, near]
        fake_session_cm = MagicMock(__enter__=MagicMock(return_value=fake_session), __exit__=MagicMock(return_value=False))

        with patch.object(retrieval, "Session", return_value=fake_session_cm):
            results = retrieval.retrieve_relevant_docs("any query", top_k=2)

        self.assertEqual(results, ["near", "far"])


class RetrieveRelevantDocsPostgresPathTests(unittest.TestCase):
    """Confirms the real pgvector query path still runs -- unchanged -- when
    the engine dialect is postgresql, without needing a live Postgres
    server: the constructed SQL is asserted directly instead of executed."""

    @patch.object(retrieval, "embed_text", return_value=[1.0, 0.0, 0.0])
    def test_postgres_dialect_uses_cosine_distance_order_by(self, mock_embed_text):
        fake_session = MagicMock()
        fake_session.exec.return_value.all.return_value = []
        fake_session_cm = MagicMock(__enter__=MagicMock(return_value=fake_session), __exit__=MagicMock(return_value=False))

        with patch.object(retrieval, "Session", return_value=fake_session_cm), \
             patch.object(retrieval.engine.dialect, "name", "postgresql"):
            retrieval.retrieve_relevant_docs("any query", top_k=3)

        fake_session.exec.assert_called_once()
        compiled_sql = str(fake_session.exec.call_args[0][0])
        self.assertIn("ORDER BY", compiled_sql)
        self.assertIn("<=>", compiled_sql)
        self.assertIn("LIMIT", compiled_sql)


if __name__ == "__main__":
    unittest.main()
