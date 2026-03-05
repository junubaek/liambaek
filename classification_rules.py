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
    "General / Other"
]


ROLE_CLUSTERS = {
    "TECH_SW": [
        "Backend Engineer", "Frontend Engineer", "Platform Engineer", "Infrastructure Engineer", 
        "Cloud Engineer", "DevOps Engineer", "Site Reliability Engineer", "Full Stack Engineer",
        "Mobile Engineer", "Android Engineer", "iOS Engineer", "Software Architect"
    ],
    "TECH_HW": [
        "Hardware Engineer", "PCB Designer", "System Integration Engineer", 
        "Embedded Software Engineer", "Firmware Engineer", "BSP Engineer", "Bootloader Engineer"
    ],
    "SEMICONDUCTOR": [
        "SoC Design Engineer", "RTL Design Engineer", "Verification Engineer", 
        "ASIC Design Engineer", "Physical Design Engineer", "Analog Design Engineer", 
        "DFT Engineer", "NPU Engineer", "ML Compiler Engineer"
    ],
    "DATA_AI": [
        "Data Engineer", "Data Scientist", "Machine Learning Engineer", "AI Engineer", 
        "Deep Learning Engineer", "MLOps Engineer", "Analytics Engineer", "Data Analyst"
    ],
    "PRODUCT": [
        "Product Manager", "Product Owner", "Service Planner", "Technical PM", "Product Analyst"
    ],
    "BUSINESS": [
        "Sales Manager", "Business Development Manager", "Account Manager", 
        "Growth Marketer", "Performance Marketer", "Brand Marketer", "SCM Planner", "Logistics Manager"
    ],
    "SECURITY": [
        "Security Engineer", "Security Operations Manager", "Compliance Manager", "Information Security Officer"
    ],
    "CORPORATE": [
        "HR Manager", "HRBP", "Recruiter", "Talent Acquisition Specialist",
        "Finance Manager", "Accounting Manager", "FP&A Analyst", 
        "Legal Counsel", "General Affairs Manager", "Strategy Planner"
    ],
    "CREATIVE": [
        "Product Designer", "UI/UX Designer", "UX Researcher", "Graphic Designer", 
        "Brand Designer", "Content Creator", "Motion Designer"
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
