import json
from typing import Dict
from app.connectors.openai_api import OpenAIClient
from app.utils.classification_rules import ROLE_CLUSTERS

class CandidateRoleClassifier:
    """
    Candidate Role Classifier: Maps resume content to Universal Role Hierarchy.
    """
    def __init__(self, openai_client: OpenAIClient):
        self.client = openai_client

    def classify_candidate(self, resume_text: str) -> str:
        clusters = json.dumps(ROLE_CLUSTERS, indent=2)
        
        prompt = f"""
You are a Senior Technical Recruiter. Based on the provided resume text, classify the candidate's core role into EXACTLY ONE of the clusters below.

[VALID CLUSTERS]
{clusters}

[RESUME TEXT]
{resume_text[:2000]}

[OUTPUT FORMAT]
Just return the cluster name (e.g., TECH_AI_DATA, CORPORATE, etc.)
"""
        try:
            # Correcting signature: get_chat_completion(system_prompt, user_message)
            role_cluster = self.client.get_chat_completion("You are a Senior Technical Recruiter.", prompt).strip()
            # Basic validation
            if role_cluster in ROLE_CLUSTERS:
                return role_cluster
            return "Unclassified"
        except Exception as e:
            print(f"❌ Role Classifier Error: {e}")
            return "Unclassified"
