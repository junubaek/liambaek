import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

class QdrantConnector:
    """
    Qdrant Connector (Phase 5): Handles multi-tenant vector isolation and similarity search.
    """
    def __init__(self, host="localhost", port=6333, api_key=None):
        self.client = QdrantClient(host=host, port=port, api_key=api_key)
        self.collection_name = "candidates_v5"

    def ensure_collection(self, vector_size=1536):
        """Ensures the v5 collection exists with appropriate indexing."""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
            print(f"✅ Qdrant Collection '{self.collection_name}' created.")

    def upsert_candidate(self, candidate_id: str, vector: list, metadata: dict, tenant_id: str = "default"):
        """Upserts candidate vector with tenant isolation metadata."""
        metadata["tenant_id"] = tenant_id
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=candidate_id,
                    vector=vector,
                    payload=metadata
                )
            ]
        )

    def find_duplicates(self, vector: list, tenant_id: str = "default", threshold: float = 0.95):
        """Finds potential duplicates using vector similarity within a tenant."""
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id))
                ]
            ),
            limit=5,
            score_threshold=threshold
        )
        return search_result

if __name__ == "__main__":
    # Setup for local dev
    connector = QdrantConnector()
    connector.ensure_collection()
