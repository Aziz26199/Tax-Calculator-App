"""tax_logic.py - Sales tax, withholding and Section 153 income tax logic (Pakistan).

NOTE: Rates below are configurable defaults. Budget changes yearly, so verify
against the latest Finance Act / authority notifications before relying on them.
"""

# ---------------- Authorities & default standard ST rates ----------------
AUTHORITIES = {
    "FBR (Goods)": 0.18,       # Sales Tax Act 1990, 11th Schedule withholding
    "FBR (ICT)":   0.15,       # ICT Tax on Services Ordinance 2001
    "SRB":         0.15,       # Sindh - verify current rate
    "PRA":         0.16,       # Punjab
    "KPRA":        0.15,       # Khyber Pakhtunkhwa
    "BRA":         0.15,       # Balochistan
}

# ---------------- Categories & sub-categories ----------------
CATEGORIES = {
    "Supplies":  ["General Goods"],
    "Services":  ["General Services", "IT / ITES", "Telecom", "Banking / Financial",
                  "Advertisement", "Renting", "Government Services",
                  "Specific Services (BRA 100%)"],
    "Contracts": ["General Contracts"],
}

TELECOM_BANKING = ("Telecom", "Banking / Financial")

# ---------------- Section 153 rates: (ATL, Non-ATL) ----------------
# Structure: IT_RATES[category][is_company] = (atl, non_atl)
IT_RATES = {
    "Supplies":  {True: (0.05, 0.10),  False: (0.055, 0.11)},
    "Services":  {True: (0.12, 0.24),  False: (0.15, 0.30)},
    "Contracts": {True: (0.075, 0.15), False: (0.08, 0.16)},
}
IT_SERVICES_IT_RATE = (0.04, 0.08)   # IT / ITES services, any person


def default_st_rate(authority):
    return AUTHORITIES[authority]


def income_tax_rate(category, subcategory, atl_active, is_company):
    """Section 153 withholding rate. Applied on Gross (Base + ST)."""
    if category == "Services" and subcategory == "IT / ITES":
        pair = IT_SERVICES_IT_RATE
    else:
        pair = IT_RATES[category][bool(is_company)]
    return pair[0] if atl_active else pair[1]


def st_withholding_fraction(authority, subcategory, st_registered, is_company, st_rate):
    """Fraction (0..1) of the sales tax that the withholding agent deducts."""
    reduced = st_rate < AUTHORITIES[authority] - 1e-9

    if authority in ("FBR (Goods)", "FBR (ICT)"):
        # Standard: 1/5th for registered, 100% for unregistered
        return 0.20 if st_registered else 1.0

    if authority == "BRA":
        if (not st_registered) or subcategory == "Specific Services (BRA 100%)" or reduced:
            return 1.0
        return 0.20

    if authority == "KPRA":
        if (not st_registered) or subcategory == "Government Services" or reduced:
            return 1.0
        return 0.50

    if authority == "PRA":
        if st_registered and is_company:          # active company exception
            return 0.80 if subcategory in TELECOM_BANKING else 0.20
        return 1.0

    if authority == "SRB":
        if subcategory in TELECOM_BANKING:
            return 0.0
        if (not st_registered) or subcategory in ("Renting", "Advertisement") or reduced:
            return 1.0
        return 0.20

    raise ValueError(f"Unknown authority: {authority}")


def calculate(base, authority, category, subcategory, st_registered,
              atl_active, is_company, st_rate=None):
    """Forward calculation from Base Invoice Value."""
    if st_rate is None:
        st_rate = default_st_rate(authority)
    frac = st_withholding_fraction(authority, subcategory, st_registered, is_company, st_rate)
    it_rate = income_tax_rate(category, subcategory, atl_active, is_company)

    st = base * st_rate
    gross = base + st
    st_withheld = st * frac
    it_withheld = gross * it_rate            # Section 153 on Gross
    net = gross - st_withheld - it_withheld
    return {
        "base": base, "st_rate": st_rate, "st": st,
        "st_wh_frac": frac, "st_withheld": st_withheld,
        "gross": gross, "it_rate": it_rate, "it_withheld": it_withheld,
        "net": net,
    }


def reverse_gross_up(net, authority, category, subcategory, st_registered,
                     atl_active, is_company, st_rate=None):
    """Reverse working: Net Payment -> Base, ST, withheld taxes, Gross.

    Base = Net / (1 + r - r*f - (1 + r) * t)
      r = ST rate, f = ST withheld fraction, t = IT rate
    """
    if st_rate is None:
        st_rate = default_st_rate(authority)
    f = st_withholding_fraction(authority, subcategory, st_registered, is_company, st_rate)
    t = income_tax_rate(category, subcategory, atl_active, is_company)
    denom = 1 + st_rate - st_rate * f - (1 + st_rate) * t
    if denom <= 0:
        raise ValueError("Rates ka combination invalid hai (denominator <= 0).")
    base = net / denom
    return calculate(base, authority, category, subcategory, st_registered,
                     atl_active, is_company, st_rate)
