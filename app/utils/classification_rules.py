ALLOWED_ROLES = [
    "Backend Engineer",
    "Frontend Engineer",
    "Full Stack Engineer",
    "Android Engineer",
    "iOS Engineer",
    "DevOps / SRE",
    "Data Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "Product Manager",
    "Project Manager",
    "UI/UX Designer",
    "Product Designer",
    "Graphic Designer",
    "Marketing Manager",
    "Sales Manager",
    "Business Analyst",
    "QA Engineer",
    "Security Engineer",
    "CTO / VPE",
    "Founder / CEO", 
    "Unclassified"
]

ALLOWED_DOMAINS = [
    "Fintech",
    "E-commerce",
    "SaaS / B2B",
    "Healthcare / Bio",
    "Edutech",
    "Mobility / Logistics",
    "Media / Content",
    "Game",
    "Blockchain / Web3",
    "AI / ML",
    "IoT / Hardware",
    "Social Media",
    "O2O / Platform",
    "Adtech",
    "Travel / Hospitality",
    "Real Estate / Proptech",
    "Finance / Strategy",
    "General / Other"
]


ROLE_CLUSTERS = {
    "SW_BACKEND": [
        "Backend Engineer", "Platform Engineer", "Infrastructure Engineer", 
        "Cloud Engineer", "DevOps / SRE", "Full Stack Engineer", "Engineering Manager"
    ],
    "SW_FRONTEND": [
        "Frontend Engineer", "Mobile Engineer", "iOS Engineer", "Android Engineer", "UI Engineer"
    ],
    "DATA_ANALYTICS": [
        "Data Analyst", "Business Analyst", "Analytics Engineer", "BI Manager", "Product Analyst"
    ],
    "DATA_SCIENCE": [
        "Data Scientist", "Data Engineer", "Machine Learning Engineer", "AI Engineer", "Deep Learning Engineer"
    ],
    "FINANCE_STRATEGY": [
        "FP&A Manager", "Financial Planning Analyst", "Strategy Analyst", "Strategy Manager", 
        "Corporate Strategy Manager", "Business Development Manager", "Accounting Manager"
    ],
    "CORPORATE_OPERATIONS": [
        "GA Manager", "General Affairs Manager", "Office Manager", "Administration Manager", 
        "Facilities Manager", "Compliance Manager", "Legal Counsel"
    ],
    "HR_TALENT": [
        "HR Manager", "Recruiter", "Talent Acquisition Specialist", "HR Business Partner", "People Operations"
    ],
    "SECURITY_ENGINEERING": [
        "Security Engineer", "Infra Security Engineer", "Application Security Engineer", "CISO"
    ],
    "MARKETING_GROWTH": [
        "Marketing Manager", "Growth Marketer", "Performance Marketer", "Content Marketer", "Brand Manager"
    ],
    "PRODUCT_PLANNING": [
        "Product Manager", "Product Owner", "Service Planner", "Project Manager"
    ],
    "DESIGN": [
        "Product Designer", "UI/UX Designer", "Graphic Designer"
    ],
    "LEADERSHIP": [
        "CTO / VPE", "Founder / CEO", "Director", "Technical Lead"
    ]
}

def get_role_cluster(role):
    for cluster, roles in ROLE_CLUSTERS.items():
        if role in roles:
            return cluster
    return "Unclassified"

def validate_role(role, fallback="Unclassified"):
    if role in ALLOWED_ROLES:
        return role
    # Fuzzy match could go here? For now strict.
    return fallback

def validate_domains(role, domains):
    # Ensure all domains are in ALLOWED_DOMAINS
    valid_domains = [d for d in domains if d in ALLOWED_DOMAINS]
    
    # If no valid domains, maybe infer from role? (Optional)
    # For now just return valid ones.
    return valid_domains
