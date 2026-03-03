import os
import json
import time
import concurrent.futures
from resume_parser import ResumeParser
from headhunting_engine.normalization.resume_normalizer import ResumeNormalizer
from connectors.openai_api import OpenAIClient
import PyPDF2
from docx import Document

class BatchReparser:
    def __init__(self, dictionary_path):
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        
        from headhunting_engine.matching.scorer import Scorer
        from headhunting_engine.matching.version_manager import VersionManager
        from headhunting_engine.analytics.drift_detector import DriftDetector
        
        self.openai = OpenAIClient(secrets["OPENAI_API_KEY"])
        self.parser = ResumeParser(self.openai)
        self.normalizer = ResumeNormalizer(dictionary_path)
        self.version_manager = VersionManager(self.normalizer.version)
        self.scorer = Scorer(self.version_manager)
        self.drift_detector = DriftDetector("headhunting_engine/analytics/v1.3.1_gold_baseline.json")
        
    def extract_text(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == '.pdf':
                text = ""
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                return text
            elif ext == '.docx':
                doc = Document(filepath)
                return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            return None
        return None

    def process_file(self, filepath):
        text = self.extract_text(filepath)
        if not text or len(text.strip()) < 100:
            return None
        
        # 1. Parse via LLM (v1.3 Schema)
        parsed = self.parser.parse(text)
        if not parsed:
            return None
        
        # 2. Normalize Skills with Depth (v1.3)
        skills_depth = parsed.get("skills_depth", [])
        norm_skills = self.normalizer.normalize_skills_depth(skills_depth)
        
        # 3. Calculate Deterministic Scores (v1.3.1 Precision)
        signals = parsed.get("quant_signals", {})
        basics = parsed.get("basics", {})
        
        # Inject context for Scorer penalties
        signals["total_years_experience"] = basics.get("total_years_experience", 0)
        
        # Calculate Mention Ratio for Depth Inflation penalty
        if norm_skills:
            mentions = [s for s in norm_skills if s.get("depth") == "Mentioned"]
            signals["mention_ratio"] = len(mentions) / len(norm_skills)
        else:
            signals["mention_ratio"] = 0
            
        raw_base_talent_score, talent_details = self.scorer.calculate_base_talent_score(signals)
        trajectory = self.scorer.calculate_trajectory(signals)
        
        candidate = {
            "id": os.path.basename(filepath),
            "name": basics.get("name", "Unknown"),
            "position": basics.get("position", "Unclassified"),
            "skills_depth": norm_skills,
            "canonical_skill_nodes": [s["name"] for s in norm_skills],
            "raw_base_talent_score": raw_base_talent_score,
            "talent_score_details": talent_details,
            "base_talent_score": raw_base_talent_score,
            "career_path_grade": trajectory,
            "career_trajectory": trajectory,
            "quant_signals": signals,
            "domain_match": True,
            "company_size_match": True
        }
        return candidate

    def apply_normalization(self, candidates):
        """
        [v1.3] Z-score normalization (Mean 65, StdDev 10)
        """
        import statistics
        scores = [c["base_talent_score"] for c in candidates if c.get("base_talent_score") is not None]
        if len(scores) < 2:
            return candidates
            
        mean = statistics.mean(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 1.0
        
        for c in candidates:
            raw = c.get("raw_base_talent_score", 50.0)
            z = (raw - mean) / std if std != 0 else 0
            normalized = 65 + (z * 10)
            c["base_talent_score"] = round(max(40, min(85, normalized)), 2)
            c["normalized_talent_score"] = c["base_talent_score"]
        return candidates

    def apply_quotas(self, candidates):
        """
        [v1.3] Enforce Grade Quotas: S(5%), A(15%), B(40%), C(25%), D(15%)
        """
        candidates.sort(key=lambda x: x["base_talent_score"], reverse=True)
        n = len(candidates)
        if n == 0: return candidates

        for i, c in enumerate(candidates):
            rank_pct = (i + 1) / n
            if rank_pct <= 0.05: c["career_path_grade"] = "S"
            elif rank_pct <= 0.20: c["career_path_grade"] = "A"
            elif rank_pct <= 0.60: c["career_path_grade"] = "B"
            elif rank_pct <= 0.85: c["career_path_grade"] = "C"
            else: c["career_path_grade"] = "D"
        return candidates

    def run_batch(self, directories, output_path, limit=100):
        all_files = []
        for d in directories:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.lower().endswith(('.pdf', '.docx')):
                        all_files.append(os.path.join(d, f))
        
        files_to_process = all_files[:limit]
        print(f"🚀 Starting Parallel Batch Reparse (Limit: {limit}, Workers: 5)...")
        processed = []
        self.drift_detector.reset_batch()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {executor.submit(self.process_file, f): f for f in files_to_process}
            
            count = 0
            for future in concurrent.futures.as_completed(future_to_file):
                f = future_to_file[future]
                try:
                    res = future.result()
                    if res:
                        processed.append(res)
                        self.drift_detector.add_sample(res)
                except Exception as e:
                    print(f"❌ Error processing {f}: {e}")
                
                count += 1
                if count % 20 == 0:
                    self.drift_detector.check_drift()
                    
                if count % 10 == 0:
                    with open(output_path + ".partial", 'w', encoding='utf-8') as partial_f:
                        json.dump(processed, partial_f, indent=2, ensure_ascii=False)
                    print(f"💾 Snapshot saved ({len(processed)} / {count} done)")
                print(f"[{count}/{limit}] Finished: {os.path.basename(f)}")

        # [v1.3] Apply Global Normalization & Quotas
        print("⚖️ Applying Z-score Normalization & Quotas...")
        processed = self.apply_normalization(processed)
        processed = self.apply_quotas(processed)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Batch Reparse Complete. Saved {len(processed)} candidates to {output_path}")

if __name__ == "__main__":
    DICT_PATH = r"headhunting_engine\dictionary\canonical_dictionary_v1.json"
    DIRS = [
        r"C:\Users\cazam\Downloads\02_resume 전처리", # PDFs and modern docx
        r"C:\Users\cazam\Downloads\02_resume_converted_docx" # Converted ones
    ]
    OUTPUT = "headhunting_engine/analytics/reparsed_pool_v1.2.json"
    
    reparser = BatchReparser(DICT_PATH)
    reparser.run_batch(DIRS, OUTPUT, limit=2500) # Mass Expansion Batch (N=2,500)
