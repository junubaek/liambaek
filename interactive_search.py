
import sys
from matcher import search_candidates

def main():
    print("=========================================")
    print("      AI Headhunter - Search Mode")
    print("=========================================")
    print("Type or Paste the Job Description (JD) below.")
    print("When finished, press ENTER explicitly on a new line to search.")
    print("-----------------------------------------")
    
    lines = []
    print("JD > ", end="", flush=True)
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            # Simple way to detect end of input for casual user: empty line
            if line.strip() == "":
                break
            lines.append(line)
        except KeyboardInterrupt:
            break
            
    jd_text = "".join(lines)
    
    if not jd_text.strip():
        print("\n[!] No JD entered. Using Default Demo JD.")
        jd_text = "Ethernet Firmware Engineer, Layer 2/3 protocols, 5 years experience, RoCE"
    
    print(f"\nSearching for:\n{jd_text[:100]}...\n")
    search_candidates(jd_text, limit=5)
    
    print("\nDone.")

if __name__ == "__main__":
    main()
