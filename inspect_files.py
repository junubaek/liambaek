
import os
from collections import Counter

target_dir = r"C:\Users\cazam\Downloads\02_resume 전처리"

def count_extensions(directory):
    counts = Counter()
    total = 0
    try:
        if not os.path.exists(directory):
            print(f"Directory not found: {directory}")
            return

        for root, _, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                counts[ext] += 1
                total += 1
        
        print(f"Total files: {total}")
        for ext, count in counts.most_common():
            print(f"{ext}: {count}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    count_extensions(target_dir)
