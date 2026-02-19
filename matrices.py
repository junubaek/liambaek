from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any

@dataclass
class Competency:
    name: str
    weight: int
    # Function that takes candidate metadata and returns True/False (or score contribution)
    # Simple boolean matching for now
    match_keywords: List[str] = field(default_factory=list)
    custom_logic: Callable[[Dict[str, Any]], bool] = None

@dataclass
class ScoreMatrix:
    name: str
    competencies: List[Competency]
    base_threshold: int

# --- Helper Logic Functions ---

def is_role_match(meta: Dict[str, Any], keywords: List[str]) -> bool:
    title = meta.get('title', '').lower().replace(" ", "")
    role_cluster = meta.get('role_cluster', '').lower()
    
    for k in keywords:
        k_clean = k.lower().replace(" ", "")
        if k_clean in title or k_clean in role_cluster:
            return True
    return False

def has_skill_match(meta: Dict[str, Any], keywords: List[str]) -> bool:
    # Check skills list (if available) or raw text in summary/body
    # Assuming meta has 'skills' list or we check 'summary'
    skills = [s.lower() for s in meta.get('skills', [])]
    summary = meta.get('summary', '').lower()
    
    for k in keywords:
        k_lower = k.lower()
        if k_lower in skills:
            return True
        if k_lower in summary:
            return True
    return False

def check_tech_collab(meta: Dict[str, Any]) -> bool:
    # Custom logic for PM/PO collaboration with devs
    keywords = ["development", "engineering", "devs", "개발자", "엔지니어", "협업"]
    summary = meta.get('summary', '').lower()
    return any(k in summary for k in keywords)

def check_data_driven(meta: Dict[str, Any]) -> bool:
    keywords = ["sql", "data analysis", "ab test", "데이터", "지표", "ga4", "amplitude"]
    return has_skill_match(meta, keywords)

def check_strategy(meta: Dict[str, Any]) -> bool:
    keywords = ["roadmap", "strategy", "kpi", "go-to-market", "로드맵", "전략", "사업"]
    return has_skill_match(meta, keywords)

# --- Matrix Definitions ---

# 1. PM/PO Matrix
PM_PO_MATRIX = ScoreMatrix(
    name="PM_PO",
    base_threshold=4,
    competencies=[
        Competency(
            name="Core Role",
            weight=3,
            match_keywords=["Product Owner", "PM", "Service Planner", "기획", "Product Manager"],
            custom_logic=lambda m: is_role_match(m, ["Product Owner", "PM", "Service Planner", "기획", "Product Manager"])
        ),
        Competency(
            name="Tech Collab",
            weight=2,
            custom_logic=check_tech_collab
        ),
        Competency(
            name="Data Driven",
            weight=1,
            custom_logic=check_data_driven
        ),
        Competency(
            name="Strategy",
            weight=1,
            custom_logic=check_strategy
        )
    ]
)

# 2. NPU Engineer Matrix
NPU_MATRIX = ScoreMatrix(
    name="NPU_System_SW",
    base_threshold=5,
    competencies=[
        Competency(
            name="Core Hard Skill",
            weight=3,
            match_keywords=["C++", "C", "System Programming", "Systems"],
            custom_logic=lambda m: has_skill_match(m, ["C++", "C", "System Programming", "Systems Engineer", "Embedded"])
        ),
        Competency(
            name="Domain Keyword",
            weight=3,
            match_keywords=["NPU", "AI Accelerator", "GPU", "Compiler", "On-device"],
            custom_logic=lambda m: has_skill_match(m, ["NPU", "AI Accelerator", "GPU", "Compiler", "On-device AI"])
        ),
        Competency(
            name="System Layer",
            weight=2,
            match_keywords=["Driver", "Kernel", "Linux", "BSP", "OS"],
            custom_logic=lambda m: has_skill_match(m, ["Driver", "Kernel", "Linux", "BSP", "Operating System"])
        ),
        Competency(
            name="Frameworks",
            weight=1,
            match_keywords=["PyTorch", "TensorFlow", "CUDA"],
            custom_logic=lambda m: has_skill_match(m, ["PyTorch", "TensorFlow", "CUDA", "OpenCL"])
        )
    ]
)

# 3. Universal Matrix (Default)
UNIVERSAL_MATRIX = ScoreMatrix(
    name="Universal",
    base_threshold=2,
    competencies=[
        Competency(
            name="Role Relevance",
            weight=3,
            # Logic will be injected dynamically based on inferred_role in the filter
            custom_logic=lambda m: False # Placeholder, overridden in filter
        ),
        Competency(
            name="Skill Overlap",
            weight=2,
            custom_logic=lambda m: False # Placeholder
        )
    ]
)


# --- Dynamic Matrix Generation ---

def generate_contract_matrix(contract: Dict[str, Any], base_matrix_name: str = "Dynamic") -> ScoreMatrix:
    """
    Creates a ScoreMatrix based on Sections in the Search Contract
    """
    competencies = []
    
    # 1. Must Core Skills (High Weight)
    must_skills = contract.get("must_core", [])
    for skill in must_skills:
        competencies.append(Competency(
            name=f"Must: {skill}",
            weight=3, # High impact
            match_keywords=[skill],
            custom_logic=lambda m, s=skill: has_skill_match(m, [s])
        ))
        
    # 2. Nice Skills (Medium Weight)
    nice_skills = contract.get("nice", [])
    for skill in nice_skills:
        competencies.append(Competency(
            name=f"Nice: {skill}",
            weight=1,
            match_keywords=[skill],
            custom_logic=lambda m, s=skill: has_skill_match(m, [s])
        ))
        
    # 3. Domain Optional (Medium Weight)
    domains = contract.get("domain_optional", [])
    for dom in domains:
         competencies.append(Competency(
            name=f"Domain: {dom}",
            weight=2,
            match_keywords=[dom],
            custom_logic=lambda m, s=dom: has_skill_match(m, [s])
        ))

    # Base Role Check (Always include a simplified role check)
    role_family = contract.get("role_family", "General")
    competencies.append(Competency(
        name="Role Alignment",
        weight=2,
        match_keywords=[role_family],
        custom_logic=lambda m: is_role_match(m, [role_family, "Product Owner", "PM", "Service Planner", "기획"] if role_family in ["PM/PO", "PM"] else [role_family])
    ))

    return ScoreMatrix(
        name=f"{base_matrix_name}_{len(competencies)}",
        base_threshold=3, # Dynamic threshold logic in filter will adjust this
        competencies=competencies
    )

def get_matrix_for_role(context: Dict[str, Any]) -> ScoreMatrix:
    """
    Returns appropriate matrix. 
    1. If Search Contract exists, generate Dynamic Matrix.
    2. Else, fallback to Static Matrix based on 'inferred_role'.
    """
    contract = context.get('search_contract')
    if contract and (contract.get('must_core') or contract.get('role_family')):
        print(f"DEBUG: Using Dynamic Contract Matrix (Must: {len(contract.get('must_core', []))})")
        return generate_contract_matrix(contract)
        
    # Fallback
    inferred_role = context.get('inferred_role', 'Universal')
    role_lower = inferred_role.lower()
    
    if "product" in role_lower or "pm" in role_lower or "기획" in role_lower:
        return PM_PO_MATRIX
    
    if "npu" in role_lower or "system" in role_lower or "compiler" in role_lower:
        return NPU_MATRIX
        
    return UNIVERSAL_MATRIX
