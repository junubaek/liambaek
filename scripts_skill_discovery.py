import os
import json
import random
import time
import urllib.parse
import win32com.client
import pythoncom
import PyPDF2
from docx import Document
from connectors.openai_api import OpenAIClient

class SkillDiscoveryEngine:
    def __init__(self, resume_dir: str):
        self.resume_dir = resume_dir
        
        # Load API Key from secrets.json
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        
        self.openai = OpenAIClient(secrets["OPENAI_API_KEY"])
        
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
            elif ext == '.doc':
                pythoncom.CoInitialize()
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                abs_path = os.path.abspath(filepath)
                doc = word.Documents.Open(abs_path)
                text = doc.Range().Text
                doc.Close()
                word.Quit()
                return text
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return ""
        return ""

    def discover_skills_from_file(self, filepath):
        content = self.extract_text(filepath)
        if not content or len(content.strip()) < 100:
            return []
            
        prompt = f"""
        You are a Technical Skill Extractor. Extract all technical skills, programming languages, and tools.
        
        [RESUME TEXT]
        {content[:8000]}
        
        [INSTRUCTIONS]
        - Output a JSON object with a "skills" key containing a list of strings.
        - Example: {{"skills": ["Python", "Docker", "PyTorch"]}}
        - Focus on HARD skills only.
        """
        
        try:
            result = self.openai.get_chat_completion_json(prompt)
            if result and isinstance(result, dict) and "skills" in result:
                return result["skills"]
        except Exception as e:
            print(f"LLM Error: {e}")
        return []

    def run(self, sample_size=30):
        all_files = []
        tech_keywords = ['개발', 'sw', 'it', 'ai', 'data', '엔지니어', 'engineer', 'backend', 'frontend', 'python', 'java', 'c++', 'linux', 'cloud', 'aws']
        
        tech_files = []
        other_files = []
        
        for root, dirs, files in os.walk(self.resume_dir):
            for f in files:
                if f.lower().endswith(('.pdf', '.docx', '.doc')):
                    path = os.path.join(root, f)
                    if any(kw in f.lower() for kw in tech_keywords):
                        tech_files.append(path)
                    else:
                        other_files.append(path)
        
        # Mix tech and others (favoring tech)
        num_tech = min(int(sample_size * 0.8), len(tech_files))
        num_others = min(sample_size - num_tech, len(other_files))
        
        sample_files = random.sample(tech_files, num_tech) + random.sample(other_files, num_others)
        print(f"🚀 Sampling {len(sample_files)} resumes (Tech: {num_tech}, Other: {num_others})...")
        
        global_skills = Counter()
        
        for i, filepath in enumerate(sample_files):
            filename = os.path.basename(filepath)
            print(f"[{i+1}/{len(sample_files)}] Processing {filename}...")
            skills = self.discover_skills_from_file(filepath)
            if skills:
                print(f"   -> Found: {', '.join(skills[:5])}...")
            for s in skills:
                global_skills[s] += 1
            time.sleep(0.5)
            
        return global_skills

from collections import Counter

if __name__ == "__main__":
    RESUME_DIR = r"C:\Users\cazam\Downloads\02_resume 전처리"
    engine = SkillDiscoveryEngine(RESUME_DIR)
    results = engine.run(sample_size=20)
    
    # Save results
    output_dir = "headhunting_engine/dictionary"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_path = os.path.join(output_dir, "skill_discovery_results.json")
    discovery_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample_size": 20,
        "discovered_skills": results.most_common(100)
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(discovery_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ Skill Discovery Complete. Results saved to {output_path}")
    print("\nTop 20 Discovered Skills:")
    for skill, count in results.most_common(20):
        print(f" - {skill}: {count}")
