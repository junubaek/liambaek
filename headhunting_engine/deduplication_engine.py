
import json
import os
import sys

class DeduplicationEngine:
    def __init__(self, pinecone_client):
        self.pc = pinecone_client

    def find_duplicates(self, query_vector, threshold=0.95):
        """
        Queries Pinecone to find potential duplicates based on vector similarity.
        Cosine Similarity > 0.95 is usually a very strong match for similar resumes.
        """
        res = self.pc.query(vector=query_vector, top_k=10, namespace="ns1")
        
        potential_dupes = []
        if res and 'matches' in res:
            for match in res['matches']:
                if match['score'] >= threshold:
                    potential_dupes.append({
                        "id": match['id'],
                        "name": match['metadata'].get('name'),
                        "score": match['score'],
                        "notion_id": match['metadata'].get('candidate_id')
                    })
        return potential_dupes

    def cleanup_old_versions(self, duplicates):
        """
        Logic to decide which one to keep (e.g. keep most recently edited in Notion).
        """
        if len(duplicates) <= 1:
            return None
            
        # Sort by score or metadata (e.g. last_edited_time if available)
        # For now, flag all but the top match as 'redundant'
        redundant = duplicates[1:]
        return redundant

if __name__ == "__main__":
    # Test would require a query_vector
    pass
