# tax_logic.py - Complete dynamic tax calculation based on Finance Act 2026 & Provincial Laws

AUTHORITIES = {
    "FBR (Goods)": 0.18,
    "FBR (ICT)": 0.15,
    "SRB": 0.13,
    "PRA": 0.16,
    "KPRA": 0.15,
    "BRA": 0.15
}

CATEGORIES = {
    "Supplies": ["General Supplies", "Edible Oils / Rice", "Toll Manufacturing"],
    "Services": ["General Services", "IT & IT Enabled Services", "Independent Professionals (Doctors, Lawyers, etc.)", "Media Advertising", "Port Operating Services"],
    "Contracts": ["General Contracts", "Sports Persons"]
}

def default_st_rate(authority):
    return AUTHORITIES.get(authority, 0.15)

def get_rates(authority, category, subcategory, st_registered, atl_active, is_company):
    # 1. Sales Tax Withholding Fraction (Provincial & FBR Rules)
    st_wh_frac = 0.0
    if not st_registered:
        st_wh_frac = 1.0  # 100% withholding for unregistered persons across all boards
    else:
        if authority == "SRB":
            st_wh_frac = 0.20  # Standard 1/5th
        elif authority == "PRA":
            st_wh_frac = 0.20 if is_company else 1.0  # Active companies 20%, others 100% generally
        elif authority == "KPRA":
            st_wh_frac = 0.50  # Standard 50%
        elif authority == "BRA":
            st_wh_frac = 0.20  # Standard 1/5th
        elif authority in ["FBR (Goods)", "FBR (ICT)"]:
            st_wh_frac = 0.20  # Standard 1/5th for FBR 11th Schedule active

    # 2. Income Tax Rate (Section 153)
    it_rate = 0.0
    
    if category == "Supplies":
        if is_company:
            it_rate = 0.05 if atl_active else 0.10
        else:
            it_rate = 0.055 if atl_active else 0.11
            
    elif category == "Services":
        if subcategory == "IT & IT Enabled Services":
            it_rate = 0.04 if atl_active else 0.08
        elif subcategory == "Independent Professionals (Doctors, Lawyers, etc.)":
            it_rate = 0.15 if atl_active else 0.30
        elif subcategory == "Media Advertising":
            it_rate = 0.015 if atl_active else 0.03
        elif subcategory == "Port Operating Services":
            it_rate = 0.12 if atl_active else 0.24
        else:
            if is_company:
                it_rate = 0.12 if atl_active else 0.24
            else:
                it_rate = 0.15 if atl_active else 0.30
                
    elif category == "Contracts":
        if is_company:
            it_rate = 0.075 if atl_active else 0.15
        else:
            it_rate = 0.08 if atl_active else 0.16

    return st_wh_frac, it_rate

def calculate(base_value, authority, category, subcategory, st_registered, atl_active, is_company, st_rate):
    if base_value < 0:
        raise ValueError("Base value negative nahi ho sakti.")
        
    st_wh_frac, it_rate = get_rates(authority, category, subcategory, st_registered, atl_active, is_company)
    
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

def reverse_gross_up(net_payment, authority, category, subcategory, st_registered, atl_active, is_company, st_rate):
    if net_payment <= 0:
        raise ValueError("Net payment zero se zyada honi chahiye.")
        
    st_wh_frac, it_rate = get_rates(authority, category, subcategory, st_registered, atl_active, is_company)
    
    # Formula: Net = Base * [1 + st_rate - (st_rate * st_wh_frac) - ((1 + st_rate) * it_rate)]
    factor = 1 + st_rate - (st_rate * st_wh_frac) - ((1 + st_rate) * it_rate)
    
    if factor <= 0:
        raise ValueError("Taxes itne zyada hain ke reverse calculation mumkin nahi.")
        
    base_value = net_payment / factor
    return calculate(base_value, authority, category, subcategory, st_registered, atl_active, is_company, st_rate)
