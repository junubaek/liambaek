
import os

target_dir = r"C:\Users\cazam\Downloads\02_resume 전처리"

for root, _, files in os.walk(target_dir):
    for file in files:
        if file.lower().endswith(".doc"):
            print(os.path.join(root, file))
            exit(0)
