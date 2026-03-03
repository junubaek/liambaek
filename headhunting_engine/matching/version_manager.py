import datetime

class VersionManager:
    """
    Centralizes versioning and metadata for the Matching Engine.
    Ensures reproducibility of scoring results.
    """
    ENGINE_VERSION = "1.0.0"
    SCORING_VERSION = "1.0"
    
    def __init__(self, dictionary_version: str):
        self.dictionary_version = dictionary_version

    def get_metadata(self) -> dict:
        """
        Returns the metadata block to be included in all results.
        """
        return {
            "engine_version": self.ENGINE_VERSION,
            "scoring_version": self.SCORING_VERSION,
            "dictionary_version": self.dictionary_version,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    @classmethod
    def validate_reproducibility(cls, result_meta: dict, current_dict_version: str) -> bool:
        """
        Checks if the current engine can reproduce a previous result.
        """
        return (
            result_meta.get("engine_version") == cls.ENGINE_VERSION and
            result_meta.get("scoring_version") == cls.SCORING_VERSION and
            result_meta.get("dictionary_version") == current_dict_version
        )
