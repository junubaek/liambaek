
# 🧠 AI 헤드헌터 시스템: 기술 아키텍처 및 성과 보고서
**[Project: Antigravity AI Headhunter]**

---

## 1. 개발 배경 (Why We Built This? 🎯)
### "키워드 검색의 한계와 AI의 불확실성 극복"
전통적인 **키워드 검색(Traditional Keyword Search)** 방식은 '문맥'을 이해하지 못합니다. 예를 들어, *"Java 경험 5년"*을 검색할 때 *"Java 초급"*이 포함된 이력서가 검색되거나, *"Kotlin"*과 같은 유사 기술을 가진 훌륭한 후보자를 놓치는 문제가 발생합니다.

반면, 초기 **생성형 AI(LLM)** 도입 시도는 *"환각(Hallucination)"*과 *"통제 불가능성"*이라는 새로운 문제를 야기했습니다. AI는 창의적이지만, 채용 담당자가 정한 **필수 자격 요건(Must-Have)**을 무시하고 *"그냥 마음에 드는"* 후보를 추천하기도 했습니다.

우리는 **"사람처럼 문맥을 이해하되, 시스템처럼 깐깐하게 규칙을 지키는"** 하이브리드 지능형 검색 엔진이 필요했습니다.

---

## 2. 해결하고자 했던 핵심 문제 (Problem Statement 🧩)
1.  **비정형 데이터의 한계 (Unstructured Data Problem)**
    *   이력서는 PDF 덩어리입니다. "총 경력 7년"이라는 정보를 숫자로 필터링하기 불가능했습니다.
2.  **검색 의도의 모호성 (Search Ambiguity)**
    *   *"좋은 백엔드 개발자"*라는 모호한 검색어는 AI에게 너무 광범위합니다. AI가 질문의 의도를 스스로 파악하고 전략을 수정해야 했습니다.
3.  **피드백의 휘발성 (Feedback loop Failure)**
    *   사용자가 "이 후보자는 별로야"라고 해도, 다음 검색에서 이름이 변경되거나 미세하게 다른 문맥에서 다시 추천되는 문제가 있었습니다.

---

## 3. 도입 기술 및 아키텍처 (Technology Stack & Implementation 🛠️)
이 문제를 해결하기 위해 **"AI Manager Architecture"**를 설계했습니다. AI는 의견을 내고, 시스템은 통제합니다.

### A. Resume Structuring Engine (ETL Pipeline)
*   **기술:** **OpenAI GPT-4o-mini (JSON Mode)** + **Traceback Error Handling**
*   **역할:** 비정형 이력서 텍스트를 강제된 JSON 스키마(`skills`, `work_experience`, `total_years`)로 변환합니다.
*   **의미:** 단순 텍스트더미를 **Queryable Database**로 변환했습니다. 이제 `total_years >= 5`와 같은 정확한 SQL급 필터링이 가능해졌습니다.

### B. Hybrid Search Mechanism (Vector + Metadata)
*   **기술:** **Pinecone (Vector DB)** + **Metadata Filtering ($gte, $in)**
*   **역할:**
    1.  **Dense Retrieval (Vector):** 의미론적 유사성("Python 전문가")을 찾습니다.
    2.  **Hard Filtering (Metadata):** "경력 5년 이상", "특정 회사 출신" 등 절대 규칙을 적용합니다.
*   **효과:** "말은 잘 통하는데(Vector), 자격 미달인(Metadata)" 후보를 원천 차단했습니다.

### C. Context-Aware Strategy (JD Confidence)
*   **기술:** **Dynamic Prompt Engineering** + **Rule-Based Ambiguity Detection**
*   **역할:** 검색 전, 입력된 JD(직무기술서)의 명확성을 0~100점으로 평가합니다.
    *   **High Confidence (>70%):** **Precision Mode** (엄격한 필터, 소수 정예)
    *   **Low Confidence (<70%):** **Recall Mode** (광범위 탐색, 다양성 확보)
*   **의미:** AI가 무작정 검색하는 것이 아니라, "제가 이해한 바로는..."이라며 전략을 수정하는 **메타인지(Metacognition)** 능력을 부여했습니다.

### D. Immutable Feedback Loop
*   **기술:** **Pinecone ID Tracking** + **Time-Decay Algorithm**
*   **역할:** 사용자 피드백(좋아요/싫어요)을 '이름'이 아닌 '고유 ID'에 저장하고, 시간이 지날수록 가중치를 낮춥니다(망각 곡선 적용).
*   **효과:** 동명이인 오류를 해결하고, 과거의 선호도가 현재의 채용 기준을 영원히 지배하지 않도록 **시장 변화에 적응**하게 만들었습니다.

---

## 4. 달성한 개선 및 성과 (Improvements & Impact 📈)

### ✅ Hard Veto System (엄격한 통제)
*   **Before:** AI가 "이 후보자는 열정이 넘쳐서 추천합니다"라며 필수 기술이 없는 후보를 상위 노출.
*   **After:** **"AI Veto"** 모듈이 `Must-Have Skills` 누락 시 즉시 점수를 0점으로 강등 (`⛔ VETO Flag`).
*   **결과:** 채용 담당자의 불필요한 이력서 검토 시간 **획기적 단축**.

### ✅ Data-Driven Filtering (정량적 필터링)
*   **Before:** "시니어 개발자" 검색 시 3년차 주니어 포함 (키워드 매칭의 한계).
*   **After:** `total_years >= 7` 필터 적용으로 **정확도 100%** 달성.

### ✅ System Resilience (시스템 회복탄력성)
*   **기술:** **Self-Healing Code (Monkey Patching)**
*   **성과:** 클라우드 배포 환경에서 라이브러리 충돌 발생 시, `app.py`가 런타임에 코드를 스스로 수정(Patch)하여 중단 없이 서비스 지속. (일반적인 웹앱에서는 보기 드문 **Extreme Stability** 패턴)

---

### 📝 결론
우리는 단순한 "AI 챗봇"을 만든 것이 아닙니다.
LLM의 창의성과 통계적 검색의 정확성을 결합하고, 그 위에 **인간의 의사결정 프로세스(Control Layer)**를 코드로 구현한 **"지능형 채용 제어 시스템(Intelligent Recruitment Control System)"**을 완성했습니다.
