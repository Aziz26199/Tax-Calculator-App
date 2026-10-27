import streamlit as st
import pandas as pd
import datetime
import io
import tax_logic as tl
from db_handler import DatabaseHandler, COLUMNS, HEADERS

st.set_page_config(page_title="Invoice & Tax Management System", layout="wide")

@st.cache_resource
def get_db():
    return DatabaseHandler()

db = get_db()

if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None
if 'page' not in st.session_state:
    st.session_state.page = "Calculator & Entry"

st.sidebar.title("Navigation")
menu = ["Calculator & Entry", "Invoice History & Bulk Upload", "Graphical Dashboard"]
selected_page = st.sidebar.radio("Go to", menu, index=menu.index(st.session_state.page) if st.session_state.page in menu else 0)
st.session_state.page = selected_page

def money(v):
    return f"{v:,.2f}"

def safe_str(val, default=""):
    if pd.isna(val):
        return default
    s = str(val).strip()
    if s.lower() == 'nan':
        return default
    return s

def safe_month(val, default=""):
    if pd.isna(val):
        return default
    if isinstance(val, (datetime.datetime, datetime.date, pd.Timestamp)):
        return val.strftime("%b-%Y")
    s = str(val).strip()
    if len(s) > 10 and "-" in s and ":" in s: 
        try:
            return pd.to_datetime(s).strftime("%b-%Y")
        except:
            pass
    if s.lower() == 'nan':
        return default
    return s

def safe_int(val, default=1):
    if pd.isna(val):
        return default
    try:
        return int(float(val)) if str(val).strip() != "" else default
    except:
        return default

def safe_float(val, default=0.0):
    if pd.isna(val):
        return default
    try:
        return float(val) if str(val).strip() != "" else default
    except:
        return default

# ==================== PAGE 1: CALCULATOR ====================
if st.session_state.page == "Calculator & Entry":
    st.title("Tax Calculator & Invoice Entry")
    
    rec = None
    if st.session_state.edit_id:
        rec = db.fetch_one(st.session_state.edit_id)
        if rec:
            st.info(f"Editing Invoice ID: {st.session_state.edit_id} (Invoice #: {rec['invoice_number']})")
        if st.button("Cancel Edit"):
            st.session_state.edit_id = None
            st.rerun()

    with st.container():
        st.subheader("Invoice & Client Details")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            inv_no = st.text_input("Invoice Number", value=rec['invoice_number'] if rec else "")
            
            current_month_str = datetime.date.today().strftime("%b-%Y")
            inv_month_val = rec['invoice_month'] if rec and rec.get('invoice_month') else current_month_str
            inv_month = st.text_input("Invoice Month (MMM-YY ya MMM-YYYY)", value=inv_month_val)
            
            post_date_val = datetime.datetime.strptime(rec['posting_date'], "%Y-%m-%d").date() if rec and rec.get('posting_date') else datetime.date.today()
            post_date = st.date_input("Posting Date", value=post_date_val)
            
            client = st.text_input("Client Name", value=rec['client'] if rec else "")
            ntn = st.text_input("Client NTN / CNIC", value=rec['ntn'] if rec and rec.get('ntn') else "")
            
        with c2:
            auth_options = list(tl.AUTHORITIES.keys())
            auth_idx = auth_options.index(rec['authority']) if (rec and rec.get('authority') in auth_options) else 0
            authority = st.selectbox("Tax Authority", auth_options, index=auth_idx)
            
            cat_options = list(tl.CATEGORIES.keys())
            cat_idx = cat_options.index(rec['category']) if (rec and rec.get('category') in cat_options) else 0
            category = st.selectbox("Category", cat_options, index=cat_idx)
            
            subcat_options = tl.CATEGORIES.get(category, [])
            subcat_idx = subcat_options.index(rec['subcategory']) if (rec and rec.get('subcategory') in subcat_options) else 0
            subcategory = st.selectbox("Sub-Category", subcat_options, index=subcat_idx if subcat_options else 0)

        with c3:
            default_rate = tl.default_st_rate(authority) * 100
            st_rate_val = (rec['st_rate'] * 100) if (rec and rec.get('st_rate') is not None) else default_rate
            st_rate = st.number_input("Sales Tax Rate (%)", min_value=0.0, max_value=100.0, value=float(st_rate_val), step=1.0)
            
            chk_reg = st.checkbox("Service Provider ST Registered & Active?", value=bool(rec['st_registered']) if (rec and rec.get('st_registered') is not None) else True)
            chk_atl = st.checkbox("Income Tax ATL Active?", value=bool(rec['atl_active']) if (rec and rec.get('atl_active') is not None) else True)
            chk_co = st.checkbox("Service Provider is a Company?", value=bool(rec['is_company']) if (rec and rec.get('is_company') is not None) else True)
            
            auto_st_wh, auto_it_rate, _ = tl.get_rates(authority, category, subcategory, chk_reg, chk_atl, chk_co)
            
            st_wh_val = (rec.get('st_wh_frac', auto_st_wh) * 100) if rec else (auto_st_wh * 100)
            it_rate_val = (rec.get('it_rate', auto_it_rate) * 100) if rec else (auto_it_rate * 100)
            
            st_wh_input = st.number_input("Sales Tax Withholding % of ST [Editable]", min_value=0.0, max_value=100.0, value=float(st_wh_val), step=5.0)
            it_rate_input = st.number_input("Income Tax Rate % [Editable]", min_value=0.0, max_value=100.0, value=float(it_rate_val), step=0.5)
            manual_deduction_input = st.number_input("Manual Further Deduction / Adjustment", min_value=0.0, value=float(rec.get('manual_deduction', 0.0)) if rec else 0.0, step=100.0)

    is_monthly_rent = False
    if category == "Sec 155 - Rent of Immovable Property" and not chk_co:
        is_monthly_rent = st.checkbox("Is this Monthly Rent? (Auto-multiply by 12 for annual slabs)", value=True)

    st.markdown("---")
    
    is_reverse = st.toggle("Reverse Working (Net Payment se nikalo)")
    
    c_val1, c_val2 = st.columns(2)
    with c_val1:
        base_val = st.number_input("Base Invoice Value / Gross Rent", min_value=0.0, value=float(rec['base_value']) if (rec and rec.get('base_value') is not None) else 0.0, disabled=is_reverse)
    with c_val2:
        net_payment_in = st.number_input("Net Payment Received (For Reverse)", min_value=0.0, value=0.0, disabled=not is_reverse)

    params = dict(
        authority=authority,
        category=category,
        subcategory=subcategory,
        st_registered=chk_reg,
        atl_active=chk_atl,
        is_company=chk_co,
        st_rate=st_rate / 100.0,
        manual_it_rate=it_rate_input / 100.0,
        manual_st_wh_pct=st_wh_input / 100.0,
        manual_deduction=manual_deduction_input,
        is_monthly_rent=is_monthly_rent
    )

    result = None
    try:
        if is_reverse and net_payment_in > 0:
            result = tl.reverse_gross_up(net_payment_in, **params)
        elif not is_reverse and base_val >= 0:
            result = tl.calculate(base_val, **params)
    except ValueError as e:
        st.error(f"⚠ {e}")

    st.subheader("Results")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    if result:
        m1.metric("Base Value", money(result['base']))
        m2.metric("Sales Tax", money(result['st']))
        m3.metric("ST Withheld", money(result['st_withheld']))
        m4.metric("Gross Invoice", money(result['gross']))
        m5.metric("IT Withheld", money(result['it_withheld']))
        m6.metric("NET PAYABLE", money(result['net']))
        
        if st.button("Save to Database" if not st.session_state.edit_id else "Update Invoice", type="primary"):
            if not inv_no.strip() or not client.strip():
                st.warning("Invoice Number aur Client Name zaroori hain.")
            else:
                record = {
                    "invoice_number": inv_no.strip(),
                    "invoice_month": inv_month.strip(),
                    "posting_date": post_date.strftime("%Y-%m-%d"),
                    "client": client.strip(),
                    "ntn": ntn.strip(),
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

# ==================== PAGE 2: HISTORY & BULK UPLOAD ====================
elif st.session_state.page == "Invoice History & Bulk Upload":
    st.title("Invoice History, Management & Filters")
    
    with st.expander("📁 Bulk Upload Invoices via Excel / Download Sample Template"):
        col_up1, col_up2 = st.columns(2)
        
        with col_up1:
            st.markdown("#### 1. Download Sample Template")
            sample_df = pd.DataFrame(columns=[
                "invoice_number", "invoice_month", "posting_date", "client", "ntn", "authority", "category", 
                "subcategory", "st_rate", "st_registered", "atl_active", "is_company", 
                "base_value", "sales_tax", "st_withheld", "gross_value", "it_withheld", "net_payable"
            ])
            sample_loc = pd.DataFrame([{
                "invoice_number": "INV-001", "invoice_month": datetime.date.today().strftime("%b-%Y"), 
                "posting_date": str(datetime.date.today()), 
                "client": "ABC Corp", "ntn": "1234567-8",
                "authority": "FBR (Goods)", "category": "Sec 153 - Supplies", "subcategory": "General Supplies",
                "st_rate": 0.18, "st_registered": 1, "atl_active": 1, "is_company": 1,
                "base_value": 100000.0, "sales_tax": 18000.0, "st_withheld": 3600.0,
                "gross_value": 118000.0, "it_withheld": 5900.0, "net_payable": 108500.0
            }])
            sample_df = pd.concat([sample_df, sample_loc], ignore_index=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                sample_df.to_excel(writer, index=False, sheet_name='Invoices')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Download Sample Excel Template",
                data=excel_data,
                file_name="Invoice_Upload_Sample.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        with col_up2:
            st.markdown("#### 2. Upload Filled Excel File")
            uploaded_file = st.file_uploader("Apni Excel file yahan drop karein (.xlsx)", type=["xlsx"])
            if uploaded_file is not None:
                try:
                    df_upload = pd.read_excel(uploaded_file)
                    if st.button("Confirm & Import into Database"):
                        count = 0
                        for _, row in df_upload.iterrows():
                            rec_dict = {
                                "invoice_number": safe_str(row.get("invoice_number"), ""),
                                "invoice_month": safe_month(row.get("invoice_month"), datetime.date.today().strftime("%b-%Y")),
                                "posting_date": safe_str(row.get("posting_date"), str(datetime.date.today())),
                                "client": safe_str(row.get("client"), ""),
                                "ntn": safe_str(row.get("ntn"), ""),
                                "authority": safe_str(row.get("authority"), "FBR (Goods)"),
                                "category": safe_str(row.get("category"), ""),
                                "subcategory": safe_str(row.get("subcategory"), ""),
                                "st_rate": safe_float(row.get("st_rate"), 0.18),
                                "st_registered": safe_int(row.get("st_registered"), 1),
                                "atl_active": safe_int(row.get("atl_active"), 1),
                                "is_company": safe_int(row.get("is_company"), 1),
                                "base_value": safe_float(row.get("base_value"), 0.0),
                                "sales_tax": safe_float(row.get("sales_tax"), 0.0),
                                "st_withheld": safe_float(row.get("st_withheld"), 0.0),
                                "gross_value": safe_float(row.get("gross_value"), 0.0),
                                "it_withheld": safe_float(row.get("it_withheld"), 0.0),
                                "net_payable": safe_float(row.get("net_payable"), 0.0)
                            }
                            db.insert_invoice(rec_dict)
                            count += 1
                        st.success(f"Successfully imported {count} invoices from Excel!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error reading Excel file: {e}")

    st.markdown("---")
    
    # --- FILTERS SECTION ---
    st.subheader("🔍 Advanced Filters & Search")
    all_raw_rows = db.fetch_all()
    
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        search_q = st.text_input("Search Client / Invoice # / NTN")
    with f_col2:
        auth_list = ["All"] + list(tl.AUTHORITIES.keys())
        sel_auth = st.selectbox("Filter by Authority", auth_list)
    with f_col3:
        cat_list = ["All"] + list(tl.CATEGORIES.keys())
        sel_cat = st.selectbox("Filter by Category", cat_list)
    with f_col4:
        months_available = ["All"] + sorted(list(set(r['invoice_month'] for r in all_raw_rows if r['invoice_month'])))
        sel_month = st.selectbox("Filter by Invoice Month", months_available)

    rows = db.fetch_all(search=search_q.strip(), authority_filter=sel_auth, category_filter=sel_cat, month_filter=sel_month)
    
    if rows:
        df = pd.DataFrame(rows)
        df = df[COLUMNS]
        
        df_display = df.copy()
        df_display["st_registered"] = df_display["st_registered"].apply(lambda x: "Yes" if x else "No")
        df_display["atl_active"] = df_display["atl_active"].apply(lambda x: "Yes" if x else "No")
        df_display["is_company"] = df_display["is_company"].apply(lambda x: "Yes" if x else "No")
        df_display["st_rate"] = df_display["st_rate"].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "0.00%")
        
        for col in ["base_value", "sales_tax", "st_withheld", "gross_value", "it_withheld", "net_payable"]:
            df_display[col] = df_display[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "0.00")
            
        df_display.columns = HEADERS
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        total_net = sum(r['net_payable'] for r in rows)
        st.info(f"**Filtered Records:** {len(rows)}   |   **Total Net Payable:** {money(total_net)}")
        
        st.markdown("### Record Actions")
        c_act1, c_act2, c_act3 = st.columns([1, 1, 3])
        
        valid_ids = [r['id'] for r in rows]
        with c_act1:
            action_id = st.selectbox("Select Record ID", options=valid_ids if valid_ids else [0])
        
        with c_act2:
            st.write("")
            st.write("")
            if st.button("Edit Selected Record") and action_id:
                st.session_state.edit_id = action_id
                st.session_state.page = "Calculator & Entry"
                st.rerun()
                
            if st.button("Delete Selected", type="secondary") and action_id:
                db.delete_invoice(action_id)
                st.success(f"Record ID {action_id} deleted!")
                st.rerun()
                    
        with c_act3:
            st.write("")
            st.write("")
            output_exp = io.BytesIO()
            with pd.ExcelWriter(output_exp, engine='openpyxl') as writer:
                df_display.to_excel(writer, index=False, sheet_name='Exported_Invoices')
            excel_export_data = output_exp.getvalue()
            
            st.download_button(
                label="📥 Download Filtered Data as Excel",
                data=excel_export_data,
                file_name=f"Invoices_Filtered_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        st.markdown("---")
        # --- DELETE ALL INVOICES BUTTON ---
        with st.expander("⚠ Danger Zone: Delete All Records"):
            st.warning("Yeh button database ki sari invoices hamesha ke liye delete kar dega!")
            confirm_del = st.checkbox("I understand the risk, delete all records")
            if st.button("🗑 Delete ALL Invoices", type="primary") and confirm_del:
                db.delete_all_invoices()
                st.success("All invoices successfully deleted!")
                st.rerun()
    else:
        st.info("No records found matching your filters.")

# ==================== PAGE 3: GRAPHICAL DASHBOARD ====================
elif st.session_state.page == "Graphical Dashboard":
    st.title("📊 Tax & Invoice Graphical Dashboard")
    
    rows = db.fetch_all()
    if rows:
        df_dash = pd.DataFrame(rows)
        
        # Summary Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Invoices", len(df_dash))
        m2.metric("Total Base Value", money(df_dash['base_value'].sum()))
        m3.metric("Total Income Tax Withheld", money(df_dash['it_withheld'].sum()))
        m4.metric("Total Net Payable", money(df_dash['net_payable'].sum()))
        
        st.markdown("---")
        
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Tax Authority Wise Net Payable")
            auth_group = df_dash.groupby('authority')['net_payable'].sum().reset_index()
            st.bar_chart(auth_group.set_index('authority'))
            
        with g2:
            st.subheader("Category Wise Total Base Value")
            cat_group = df_dash.groupby('category')['base_value'].sum().reset_index()
            st.bar_chart(cat_group.set_index('category'))
            
        st.markdown("---")
        
        g3, g4 = st.columns(2)
        with g3:
            st.subheader("Invoice Month Wise Trend (Net Payable)")
            month_group = df_dash.groupby('invoice_month')['net_payable'].sum().reset_index()
            st.line_chart(month_group.set_index('invoice_month'))
            
        with g4:
            st.subheader("Sales Tax vs Income Tax Withheld")
            tax_compare = df_dash[['invoice_month', 'sales_tax', 'it_withheld']].copy()
            st.area_chart(tax_compare)
    else:
        st.info("Dashboard ke liye abhi koi data mojood nahi hai. Pehle kuch invoices enter ya upload karein.")
