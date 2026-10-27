# tax_logic.py - Complete dynamic tax calculation based on Finance Act 2026 & Provincial Laws

AUTHORITIES = {
    "FBR (Goods)": 0.18,
    "FBR (ICT)": 0.15,
    "SRB": 0.15,
    "PRA": 0.16,
    "KPRA": 0.15,
    "BRA": 0.15,
    "No Sales Tax (Only IT)": 0.0
}

# Subcategories updated based on Withholding Tax Rates Card (Complete)
CATEGORIES = {
    "Sec 153 - Supplies": [
        "General Supplies", 
        "Sale of rice, cotton seed or edible oils", 
        "Toll Manufacturing"
    ],
    "Sec 153 - Services": [
        "General Services", 
        "IT & IT Enabled Services", 
        "Independent Professionals (Doctors, Lawyers, Architects, etc.)", 
        "Electronic & Print Media Advertising", 
        "Terminal and Port Operating Services",
        "Sports Persons"
    ],
    "Sec 153 - Contracts": [
        "General Contracts", 
        "Sports Persons",
        "Execution of a contract (other than goods/services)"
    ],
    "Sec 153(2A) - E-Commerce": [
        "Through digital means (Payment intermediary)",
        "Cash on delivery by courier"
    ],
    "Sec 233 - Brokerage & Commission": [
        "Advertising Agents",
        "Life Insurance Agents (< 0.5M)",
        "Others"
    ],
    "Sec 155 - Rent of Immovable Property": [
        "Company (Flat Rate)",
        "Individual / AOP (Slabs apply - Use Manual Edit)"
    ],
    "Sec 154 / 154A - Exports": [
        "Export of Goods (General)",
        "IT / IT Enabled Services (PSEB Registered)",
        "Social Media Digital Content Creators",
        "Export of Services (Other)"
    ],
    "Sec 152 - Payments to Non-Residents": [
        "General Services (Other than IT)",
        "IT & IT enabled services",
        "Contracts / Execution of work"
    ]
}

def default_st_rate(authority):
    return AUTHORITIES.get(authority, 0.0)

def get_rates(authority, category, subcategory, st_registered, atl_active, is_company):
    # 1. Sales Tax Withholding Fraction
    st_wh_frac = 0.0
    if not st_registered:
        st_wh_frac = 1.0
    else:
        if authority in ["SRB", "BRA", "FBR (Goods)", "FBR (ICT)"]:
            st_wh_frac = 0.20
        elif authority == "PRA":
            st_wh_frac = 0.20 if is_company else 1.0
        elif authority == "KPRA":
            st_wh_frac = 0.50

    # 2. Income Tax Rate (Based on Withholding Card)
    it_rate = 0.0
    
    # Sec 153 - Supplies[cite: 686]
    if category == "Sec 153 - Supplies":
        if subcategory == "Sale of rice, cotton seed or edible oils":
            it_rate = 0.015 if atl_active else 0.03
        elif subcategory == "Toll Manufacturing":
            if is_company:
                it_rate = 0.09 if atl_active else 0.18
            else:
                it_rate = 0.11 if atl_active else 0.22
        else: # General Supplies
            if is_company:
                it_rate = 0.05 if atl_active else 0.10
            else:
                it_rate = 0.055 if atl_active else 0.11
                
    # Sec 153 - Services[cite: 687]
    elif category == "Sec 153 - Services":
        if subcategory == "IT & IT Enabled Services":
            it_rate = 0.04 if atl_active else 0.08
        elif subcategory == "Independent Professionals (Doctors, Lawyers, Architects, etc.)":
            it_rate = 0.15 if atl_active else 0.30
        elif subcategory == "Electronic & Print Media Advertising":
            it_rate = 0.015 if atl_active else 0.03
        elif subcategory == "Terminal and Port Operating Services":
            it_rate = 0.12 if atl_active else 0.24 
        elif subcategory == "Sports Persons":
            it_rate = 0.14 if atl_active else 0.28
        else: # General Services
            if is_company:
                it_rate = 0.12 if atl_active else 0.24
            else:
                it_rate = 0.15 if atl_active else 0.30
                
    # Sec 153 - Contracts[cite: 687, 688]
    elif category == "Sec 153 - Contracts":
        if subcategory in ["Sports Persons", "Execution of a contract (other than goods/services)"]:
            it_rate = 0.15 if atl_active else 0.30
        else: # General Contracts
            if is_company:
                it_rate = 0.075 if atl_active else 0.15
            else:
                it_rate = 0.08 if atl_active else 0.16

    # Sec 153(2A) - E-Commerce[cite: 688]
    elif category == "Sec 153(2A) - E-Commerce":
        if subcategory == "Through digital means (Payment intermediary)":
            it_rate = 0.01 if atl_active else 0.02
        else: # Cash on delivery
            it_rate = 0.02 if atl_active else 0.04

    # Sec 233 - Brokerage & Commission[cite: 692]
    elif category == "Sec 233 - Brokerage & Commission":
        if subcategory == "Advertising Agents":
            it_rate = 0.10 if atl_active else 0.20
        elif subcategory == "Life Insurance Agents (< 0.5M)":
            it_rate = 0.08 if atl_active else 0.16
        else:
            it_rate = 0.12 if atl_active else 0.24

    # Sec 155 - Rent of Immovable Property
    elif category == "Sec 155 - Rent of Immovable Property":
        if subcategory == "Company (Flat Rate)" or is_company:
            it_rate = 0.15 if atl_active else 0.30
        else:
            # For Individuals/AOPs, rent has threshold slabs (Rs. 300,000 etc.)[cite: 689]
            # UI manual editable box is used for exact slab calculation
            it_rate = 0.0 

    # Sec 154 / 154A - Exports[cite: 688]
    elif category == "Sec 154 / 154A - Exports":
        if subcategory == "Export of Goods (General)":
            it_rate = 0.0125
        elif subcategory == "IT / IT Enabled Services (PSEB Registered)":
            it_rate = 0.0025
        elif subcategory == "Social Media Digital Content Creators":
            it_rate = 0.01 if atl_active else 0.10
        else:
            it_rate = 0.01 if atl_active else 0.05

    # Sec 152 - Payments to Non-Residents[cite: 685, 686]
    elif category == "Sec 152 - Payments to Non-Residents":
        if subcategory == "IT & IT enabled services":
            it_rate = 0.04 if atl_active else 0.08
        elif subcategory == "General Services (Other than IT)":
            it_rate = 0.08 if atl_active else 0.16
        else:
            it_rate = 0.15 if atl_active else 0.30

    return st_wh_frac, it_rate

def calculate(base_value, authority, category, subcategory, st_registered, atl_active, is_company, st_rate, manual_it_rate=None):
    if base_value < 0:
        raise ValueError("Base value negative nahi ho sakti.")
        
    st_wh_frac, auto_it_rate = get_rates(authority, category, subcategory, st_registered, atl_active, is_company)
    
    # Use manual IT rate if provided, otherwise auto-calculated
    it_rate = manual_it_rate if manual_it_rate is not None else auto_it_rate
    
    st_amount = base_value * st_rate
    st_withheld = st_amount * st_wh_frac
    gross_value = base_value + st_amount
    it_withheld = gross_value * it_rate
    net_payable = gross_value - st_withheld - it_withheld
    
    return {
        "base": base_value,
        "st": st_amount,
        "st_withheld": st_withheld,
        "gross": gross_value,
        "it_withheld": it_withheld,
        "net": net_payable,
        "st_rate": st_rate,
        "st_wh_frac": st_wh_frac,
        "it_rate": it_rate
    }

def reverse_gross_up(net_payment, authority, category, subcategory, st_registered, atl_active, is_company, st_rate, manual_it_rate=None):
    if net_payment <= 0:
        raise ValueError("Net payment zero se zyada honi chahiye.")
        
    st_wh_frac, auto_it_rate = get_rates(authority, category, subcategory, st_registered, atl_active, is_company)
    it_rate = manual_it_rate if manual_it_rate is not None else auto_it_rate
    
    factor = 1 + st_rate - (st_rate * st_wh_frac) - ((1 + st_rate) * it_rate)
    
    if factor <= 0:
        raise ValueError("Taxes itne zyada hain ke reverse calculation mumkin nahi.")
        
    base_value = net_payment / factor
    return calculate(base_value, authority, category, subcategory, st_registered, atl_active, is_company, st_rate, manual_it_rate)
