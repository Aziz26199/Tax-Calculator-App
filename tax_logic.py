# tax_logic.py - Complete dynamic tax calculation based on Finance Act & Provincial Laws

AUTHORITIES = {
    "FBR (Goods)": 0.18,
    "FBR (ICT)": 0.15,
    "SRB": 0.13,
    "PRA": 0.16,
    "KPRA": 0.15,
    "BRA": 0.15,
    "No Sales Tax (Only IT)": 0.0
}

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
        "Rent of Immovable Property (Company / Individual Slabs)"
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

def get_rates(authority, category, subcategory, st_registered, atl_active, is_company, base_value=0):
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

    it_rate = 0.0
    it_fixed_amount = 0.0

    if category == "Sec 153 - Supplies":
        if subcategory == "Sale of rice, cotton seed or edible oils":
            it_rate = 0.015 if atl_active else 0.03
        elif subcategory == "Toll Manufacturing":
            it_rate = 0.09 if (atl_active and is_company) else (0.18 if is_company else (0.11 if atl_active else 0.22))
        else:
            it_rate = 0.05 if (atl_active and is_company) else (0.10 if is_company else (0.055 if atl_active else 0.11))
                
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
        else:
            it_rate = 0.12 if (atl_active and is_company) else (0.24 if is_company else (0.15 if atl_active else 0.30))
                
    elif category == "Sec 153 - Contracts":
        if subcategory in ["Sports Persons", "Execution of a contract (other than goods/services)"]:
            it_rate = 0.15 if atl_active else 0.30
        else:
            it_rate = 0.075 if (atl_active and is_company) else (0.15 if is_company else (0.08 if atl_active else 0.16))

    elif category == "Sec 153(2A) - E-Commerce":
        it_rate = 0.01 if (subcat_check := subcategory == "Through digital means (Payment intermediary)") and atl_active else (0.02 if subcat_check else (0.02 if atl_active else 0.04))

    elif category == "Sec 233 - Brokerage & Commission":
        if subcategory == "Advertising Agents":
            it_rate = 0.10 if atl_active else 0.20
        elif subcategory == "Life Insurance Agents (< 0.5M)":
            it_rate = 0.08 if atl_active else 0.16
        else:
            it_rate = 0.12 if atl_active else 0.24

    elif category == "Sec 155 - Rent of Immovable Property":
        if is_company:
            it_rate = 0.15 if atl_active else 0.30
        else:
            if not atl_active:
                it_rate = 0.30
            else:
                it_rate = 0.0  # Slabs will handle this dynamically in calculate()

    elif category == "Sec 154 / 154A - Exports":
        if subcategory == "Export of Goods (General)":
            it_rate = 0.0125
        elif subcategory == "IT / IT Enabled Services (PSEB Registered)":
            it_rate = 0.0025
        elif subcategory == "Social Media Digital Content Creators":
            it_rate = 0.01 if atl_active else 0.10
        else:
            it_rate = 0.01 if atl_active else 0.05

    elif category == "Sec 152 - Payments to Non-Residents":
        if subcategory == "IT & IT enabled services":
            it_rate = 0.04 if atl_active else 0.08
        elif subcategory == "General Services (Other than IT)":
            it_rate = 0.08 if atl_active else 0.16
        else:
            it_rate = 0.15 if atl_active else 0.30

    return st_wh_frac, it_rate, it_fixed_amount

def calculate(base_value, authority, category, subcategory, st_registered, atl_active, is_company, st_rate, manual_it_rate=None, manual_st_wh_pct=None, manual_deduction=0.0, is_monthly_rent=False):
    if base_value < 0:
        raise ValueError("Base value negative nahi ho sakti.")
        
    auto_st_wh_frac, auto_it_rate, _ = get_rates(authority, category, subcategory, st_registered, atl_active, is_company, base_value)
    
    st_wh_frac = manual_st_wh_pct if manual_st_wh_pct is not None else auto_st_wh_frac
    it_rate = manual_it_rate if manual_it_rate is not None else auto_it_rate
    
    st_amount = base_value * st_rate
    st_withheld = st_amount * st_wh_frac
    gross_value = base_value + st_amount
    
    # Sec 155 Rent Slab Logic (Fixed to check manual override properly)
    if category == "Sec 155 - Rent of Immovable Property" and not is_company and atl_active:
        if manual_it_rate is None or manual_it_rate == 0.0:
            annual_rent = (base_value * 12) if is_monthly_rent else base_value
            
            if annual_rent <= 300000:
                annual_tax = 0.0
            elif annual_rent <= 600000:
                annual_tax = (annual_rent - 300000) * 0.05
            elif annual_rent <= 2000000:
                annual_tax = 15000 + (annual_rent - 600000) * 0.10
            else:
                annual_tax = 155000 + (annual_rent - 2000000) * 0.25
                
            it_withheld = (annual_tax / 12) if is_monthly_rent else annual_tax
        else:
            it_withheld = gross_value * manual_it_rate
    else:
        it_withheld = gross_value * it_rate
        
    net_payable = gross_value - st_withheld - it_withheld - manual_deduction
    
    return {
        "base": base_value,
        "st": st_amount,
        "st_withheld": st_withheld,
        "gross": gross_value,
        "it_withheld": it_withheld,
        "manual_deduction": manual_deduction,
        "net": net_payable,
        "st_rate": st_rate,
        "st_wh_frac": st_wh_frac,
        "it_rate": it_rate
    }

def reverse_gross_up(net_payment, authority, category, subcategory, st_registered, atl_active, is_company, st_rate, manual_it_rate=None, manual_st_wh_pct=None, manual_deduction=0.0, is_monthly_rent=False):
    if net_payment <= 0:
        raise ValueError("Net payment zero se zyada honi chahiye.")
        
    adjusted_net = net_payment + manual_deduction
    auto_st_wh_frac, auto_it_rate, _ = get_rates(authority, category, subcategory, st_registered, atl_active, is_company, net_payment)
    
    st_wh_frac = manual_st_wh_pct if manual_st_wh_pct is not None else auto_st_wh_frac
    it_rate = manual_it_rate if manual_it_rate is not None else auto_it_rate
    
    factor = 1 + st_rate - (st_rate * st_wh_frac) - ((1 + st_rate) * it_rate)
    if factor <= 0:
        raise ValueError("Taxes itne zyada hain ke reverse calculation mumkin nahi.")
        
    base_value = adjusted_net / factor
    return calculate(base_value, authority, category, subcategory, st_registered, atl_active, is_company, st_rate, manual_it_rate, manual_st_wh_pct, manual_deduction, is_monthly_rent)
