# AI Headhunter System Methodology: "The AI Manager Architecture"

## 1. Core Philosophy
**"AI provides the opinion, the System provides the control."**

In this architecture, the AI (LLM) is not the decision-maker; it is a **high-level employee** (the "Quant Evaluator") whose output is strictly managed by a deterministic control layer (the "Manager").

| Component | Role | Responsibility |
| :--- | :--- | :--- |
| **LLM (GPT-4)** | Employee | Read text, extract signals, give opinion (Score 0-100). |
| **Python Code** | Manager | Decide strategy, enforce rules, veto results, manage memory. |

---

## 2. Key Mechanisms

### A. The Confidence-Strategy Loop
We do not search blindly. The system first evaluates **its own understanding** of the Job Description (JD).

1.  **JD Analysis**: The system scores the JD Clarity (0-100%).
2.  **Strategy Selection**:
    *   **High Confidence (>70%)** → **Precision Mode**: Strict filters, lower `top_k`, Role Cluster enforcement.
    *   **Low Confidence (<70%)** → **Recall Mode**: Broader search, higher `top_k`, relaxed filters.

### B. The "Hard Veto" Protocol
vector Similarity and "Likes" are not allowed to override fundamental requirements.

*   **Rule**: If a candidate misses **Must-Have Skills**, they fail (Score < 40).
*   **Enforcement**:
    *   Even if Vector Similarity is 0.95 (High match).
    *   Even if the user "Liked" this candidate in the past.
    *   **Result**: The system overwrites the score to 0 and flags: `⛔ VETO: Missed Critical Criteria`.

### C. ID-Based Memory (The Elephant's Brain)
User feedback is tracked robustly to create a learning loop that resists data noise.

*   **Identifier**: Feedback is tied to `Candidate ID` (Pinecone ID), not Name (prevents homonym errors).
*   **Time Decay**: Feedback weight decays over time (Half-life: 90 days), ensuring the system adapts to changing markets.

---

## 3. Decision Flow

```mermaid
graph TD
    A[User Inputs JD] --> B{JD Confidence?}
    B -- High --> C[Precision Search]
    B -- Low --> D[Recall Search]
    
    C & D --> E[Vector Retrieval]
    E --> F[Feedback Boost (Decayed)]
    F --> G[LLM Re-ranking (The Judge)]
    
    G --> H{Must-Haves Met?}
    H -- No --> I[HARD VETO (Score=0)]
    H -- Yes --> J[Final Score Calculation]
    
    I & J --> K[Final Ranked List]
    K --> L[Human Verification UI]
```

## 4. Why This Matters
This architecture moves beyond "calling an API" to building a **Reliable Enterprise System**. It assumes AI will make mistakes and builds safety nets (Vetos, Confidence Scores) to catch them, ensuring the human recruiter always stays in the loop but is empowered by the machine.
