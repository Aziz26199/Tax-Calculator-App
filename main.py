import streamlit as st
import pandas as pd
import datetime
import tax_logic as tl
from db_handler import DatabaseHandler, COLUMNS, HEADERS

# Page config
st.set_page_config(page_title="Invoice & Tax Calculator", layout="wide")

# Initialize Database
@st.cache_resource
def get_db():
    return DatabaseHandler()

db = get_db()

# Initialize Session State variables
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None
if 'page' not in st.session_state:
    st.session_state.page = "Calculator & Entry"

# Navigation Sidebar
st.sidebar.title("Navigation")
menu = ["Calculator & Entry", "Invoice History"]
# Update page from sidebar
selected_page = st.sidebar.radio("Go to", menu, index=menu.index(st.session_state.page))
st.session_state.page = selected_page

def money(v):
    return f"{v:,.2f}"

# ==================== PAGE 1: CALCULATOR ====================
if st.session_state.page == "Calculator & Entry":
    st.title("Tax Calculator & Invoice Entry")
    
    # Load data if editing
    rec = None
    if st.session_state.edit_id:
        rec = db.fetch_one(st.session_state.edit_id)
        st.info(f"Editing Invoice ID: {st.session_state.edit_id} (Invoice #: {rec['invoice_number']})")
        if st.button("Cancel Edit"):
            st.session_state.edit_id = None
            st.rerun()

    # Layout: Form Inputs
    with st.container():
        st.subheader("Invoice Details")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            inv_no = st.text_input("Invoice Number", value=rec['invoice_number'] if rec else "")
            date_val = datetime.datetime.strptime(rec['date'], "%Y-%m-%d").date() if rec else datetime.date.today()
            inv_date = st.date_input("Date", value=date_val)
            client = st.text_input("Client Name", value=rec['client'] if rec else "")
            
        with c2:
            auth_options = list(tl.AUTHORITIES.keys())
            auth_idx = auth_options.index(rec['authority']) if rec else 0
            authority = st.selectbox("Tax Authority", auth_options, index=auth_idx)
            
            cat_options = list(tl.CATEGORIES.keys())
            cat_idx = cat_options.index(rec['category']) if rec else 0
            category = st.selectbox("Category", cat_options, index=cat_idx)
            
            subcat_options = tl.CATEGORIES.get(category, [])
            subcat_idx = subcat_options.index(rec['subcategory']) if (rec and rec['subcategory'] in subcat_options) else 0
            subcategory = st.selectbox("Sub-Category", subcat_options, index=subcat_idx if subcat_options else 0)

with c3:
            default_rate = tl.default_st_rate(authority) * 100
            st_rate_val = (rec['st_rate'] * 100) if rec else default_rate
            st_rate = st.number_input("Sales Tax Rate (%)", min_value=0.0, max_value=100.0, value=float(st_rate_val), step=1.0)
            
            chk_reg = st.checkbox("Service Provider ST Registered & Active?", value=bool(rec['st_registered']) if rec else True)
            chk_atl = st.checkbox("Income Tax ATL Active?", value=bool(rec['atl_active']) if rec else True)
            chk_co = st.checkbox("Service Provider is a Company?", value=bool(rec['is_company']) if rec else True)
            
            # Auto-calculate default IT rate based on selections
            _, auto_it_rate = tl.get_rates(authority, category, subcategory, chk_reg, chk_atl, chk_co)
            it_rate_val = (rec.get('it_rate', auto_it_rate) * 100) if rec else (auto_it_rate * 100)
            
# Manual override option for IT Rate
    it_rate_input = st.number_input("Income Tax Rate (%) [Editable]", min_value=0.0, max_value=100.0, value=float(it_rate_val), step=0.5)
    st.markdown("---")
    
  # Financial Inputs
    is_reverse = st.toggle("Reverse Working (Net Payment se nikalo)")
    
    c_val1, c_val2 = st.columns(2)
    with c_val1:
        base_val = st.number_input("Base Invoice Value", min_value=0.0, value=float(rec['base_value']) if rec else 0.0, disabled=is_reverse)
    with c_val2:
        net_payment_in = st.number_input("Net Payment Received (For Reverse)", min_value=0.0, value=0.0, disabled=not is_reverse)

# Calculation Logic
    params = dict(
        authority=authority,
        category=category,
        subcategory=subcategory,
        st_registered=chk_reg,
        atl_active=chk_atl,
        is_company=chk_co,
        st_rate=st_rate / 100.0,
        manual_it_rate=it_rate_input / 100.0  # Naya parameter pass kar diya
    )

    result = None
    try:
        if is_reverse and net_payment_in > 0:
            result = tl.reverse_gross_up(net_payment_in, **params)
        elif not is_reverse and base_val > 0:
            result = tl.calculate(base_val, **params)
    except ValueError as e:
        st.error(f"⚠ {e}")

    # Display Results
    st.subheader("Results")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    if result:
        m1.metric("Base Value", money(result['base']))
        m2.metric("Sales Tax", money(result['st']))
        m3.metric("ST Withheld", money(result['st_withheld']))
        m4.metric("Gross Invoice", money(result['gross']))
        m5.metric("IT Withheld", money(result['it_withheld']))
        m6.metric("NET PAYABLE", money(result['net']))
        
        st.caption(f"ST rate {result['st_rate']*100:.2f}% | ST withheld {result['st_wh_frac']*100:.0f}% of ST | IT rate {result['it_rate']*100:.2f}% on Gross")
        
        # Save Button
        if st.button("Save to Database" if not st.session_state.edit_id else "Update Invoice", type="primary"):
            if not inv_no.strip() or not client.strip():
                st.warning("Invoice Number aur Client Name zaroori hain.")
            else:
                record = {
                    "invoice_number": inv_no.strip(),
                    "date": inv_date.strftime("%Y-%m-%d"),
                    "client": client.strip(),
                    "authority": authority, "category": category,
                    "subcategory": subcategory, "st_rate": st_rate / 100.0,
                    "st_registered": int(chk_reg), "atl_active": int(chk_atl),
                    "is_company": int(chk_co),
                    "base_value": round(result['base'], 2), "sales_tax": round(result['st'], 2),
                    "st_withheld": round(result['st_withheld'], 2), "gross_value": round(result['gross'], 2),
                    "it_withheld": round(result['it_withheld'], 2), "net_payable": round(result['net'], 2),
                }
                
                if st.session_state.edit_id:
                    db.update_invoice(st.session_state.edit_id, record)
                    st.success("Invoice successfully updated!")
                    st.session_state.edit_id = None
                else:
                    db.insert_invoice(record)
                    st.success("Invoice saved to database!")
    else:
        st.info("Amounts enter karein calculation dekhne ke liye.")

# ==================== PAGE 2: HISTORY ====================
elif st.session_state.page == "Invoice History":
    st.title("Invoice History")
    
    search_q = st.text_input("Search client / invoice # / authority...")
    
    rows = db.fetch_all(search_q.strip())
    
    if rows:
        df = pd.DataFrame(rows, columns=HEADERS)
        
        # Format columns for display
        df_display = df.copy()
        for col in ["Base Value", "Sales Tax", "ST Withheld", "Gross Value", "IT Withheld", "Net Payable"]:
            df_display[col] = df_display[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "0.00")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.write(f"**Total Records:** {len(rows)} | **Total Net Payable:** {money(sum(r['net_payable'] for r in rows))}")
        
        st.markdown("### Actions")
        c_act1, c_act2, c_act3 = st.columns([1, 1, 3])
        
        # Action Inputs
        with c_act1:
            action_id = st.number_input("Enter ID to Edit/Delete", min_value=1, step=1)
        
        with c_act2:
            st.write("") # spacing
            st.write("")
            if st.button("Edit Selected"):
                # Check if ID exists
                if any(r['id'] == action_id for r in rows):
                    st.session_state.edit_id = action_id
                    st.session_state.page = "Calculator & Entry"
                    st.rerun()
                else:
                    st.error("ID not found in current list.")
                    
            if st.button("Delete Selected"):
                if any(r['id'] == action_id for r in rows):
                    db.delete_invoice(action_id)
                    st.success(f"Record ID {action_id} deleted!")
                    st.rerun()
                else:
                    st.error("ID not found.")
                    
        with c_act3:
            st.write("")
            st.write("")
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download as CSV",
                data=csv_data,
                file_name=f"Invoices_Export_{datetime.date.today()}.csv",
                mime='text/csv'
            )
    else:
        st.info("No records found.")
