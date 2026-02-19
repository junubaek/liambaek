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
    "DESIGN": [
        "Product Designer", "UI/UX Designer", "Graphic Designer", "Brand Designer",
        "Interaction Designer", "Industrial Designer", "3D Designer", "Contents Designer", "Web Designer"
    ],
    "TECH_LOW_LEVEL": [
        "Firmware Engineer", "Embedded Software Engineer", "Device Driver Engineer",
        "System Software Engineer", "Kernel Engineer", "BSP Engineer", "Bootloader Engineer"
    ],
    "TECH_PLATFORM": [
        "Backend Engineer", "Platform Engineer", "Infrastructure Engineer", 
        "Cloud Engineer", "DevOps Engineer", "Site Reliability Engineer", "Full Stack Engineer"
    ],
    "TECH_AI_DATA": [
        "AI Engineer", "Machine Learning Engineer", "Deep Learning Engineer", 
        "ML Engineer", "Data Engineer", "Data Scientist", "Analytics Engineer",
        "ML Compiler Engineer", "NPU Runtime Engineer", "AI Accelerator Software Engineer"
    ],
    "TECH_HARDWARE": [
        "SoC Design Engineer", "RTL Design Engineer", "Verification Engineer", 
        "ASIC Design Engineer", "FPGA Engineer", "Physical Design Engineer", "DFT Engineer", "Product Engineer"
    ],
    "PRODUCT_PLANNING": [
        "Product Manager", "Product Owner", "Service Planner", 
        "Business Planner", "Strategy Planner", "Corporate Strategy Manager"
    ],
    "SALES_MARKETING": [
        "Sales Manager", "Account Manager", "Key Account Manager", "Business Development Manager", 
        "Sales Engineer", "Marketing Manager", "Product Marketing Manager", "Growth Marketer",
        "Performance Marketer", "Content Marketer", "Brand Manager", "Channel Sales Manager", "Overseas Sales Manager", "Digital Marketer"
    ],
    "CORPORATE": [
        "HR Manager", "HR Business Partner", "Recruiter", "Talent Acquisition Specialist",
        "People Operations Manager", "HR Development Manager",
        "Finance Manager", "Accounting Manager", "FP&A Manager", "Treasury Manager", "Tax Manager", "Financial Planning Analyst",
        "Legal Counsel", "Compliance Manager", "Corporate Counsel", 
        "General Affairs Manager", "Office Manager", "Administration Manager", "Facilities Manager"
    ],
    "OPERATION_SCM": [
        "Operations Manager", "Supply Chain Manager", "SCM Planner", "Logistics Manager", 
        "Procurement Manager", "Purchasing Manager", "Inventory Manager"
    ],
    "TECH_CLIENT": [
        "Frontend Engineer", "Mobile Engineer", "Application Software Engineer"
    ],
    "TECH_NET_SEC": [
        "Network Engineer", "Security Engineer"
    ],
    "LEADERSHIP": [
        "Technical Lead", "Software Architect", "Engineering Manager",
        "Team Lead", "Department Head", "Director"
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
