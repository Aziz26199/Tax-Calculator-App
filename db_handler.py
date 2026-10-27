import sqlite3
import pandas as pd

# Yeh line bata rahi hai ke database seedhi Z drive par bane gi
DB_FILE = r"Z:\invoices.db"

COLUMNS = [
    "id", "invoice_number", "invoice_month", "posting_date", "client", "ntn", "authority", "category", 
    "subcategory", "st_rate", "st_registered", "atl_active", "is_company", 
    "base_value", "sales_tax", "st_withheld", "gross_value", "it_withheld", "net_payable"
]

HEADERS = [
    "ID", "Invoice #", "Inv Month", "Post Date", "Client", "NTN / CNIC", "Authority", "Category", 
    "Sub-Category", "ST Rate", "ST Reg.", "ATL", "Company", 
    "Base Value", "Sales Tax", "ST Withheld", "Gross Value", "IT Withheld", "Net Payable"
]

class DatabaseHandler:
    def __init__(self):
        # Using local file path with check_same_thread=False for Streamlit multithreading safety
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            invoice_month TEXT,
            posting_date TEXT,
            client TEXT,
            ntn TEXT,
            authority TEXT,
            category TEXT,
            subcategory TEXT,
            st_rate REAL,
            st_registered INTEGER,
            atl_active INTEGER,
            is_company INTEGER,
            base_value REAL,
            sales_tax REAL,
            st_withheld REAL,
            gross_value REAL,
            it_withheld REAL,
            net_payable REAL
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def insert_invoice(self, rec):
        query = """
        INSERT INTO invoices (
            invoice_number, invoice_month, posting_date, client, ntn, authority, category, subcategory, 
            st_rate, st_registered, atl_active, is_company, 
            base_value, sales_tax, st_withheld, gross_value, it_withheld, net_payable
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        vals = (
            rec.get("invoice_number", ""), rec.get("invoice_month", ""), rec.get("posting_date", ""), 
            rec.get("client", ""), rec.get("ntn", ""), 
            rec.get("authority", ""), rec.get("category", ""), rec.get("subcategory", ""), 
            rec.get("st_rate", 0.0), rec.get("st_registered", 1), rec.get("atl_active", 1), 
            rec.get("is_company", 1), rec.get("base_value", 0.0), rec.get("sales_tax", 0.0), 
            rec.get("st_withheld", 0.0), rec.get("gross_value", 0.0), rec.get("it_withheld", 0.0), 
            rec.get("net_payable", 0.0)
        )
        self.conn.execute(query, vals)
        self.conn.commit()

    def update_invoice(self, record_id, rec):
        query = """
        UPDATE invoices SET 
            invoice_number=?, invoice_month=?, posting_date=?, client=?, ntn=?, authority=?, category=?, subcategory=?, 
            st_rate=?, st_registered=?, atl_active=?, is_company=?, 
            base_value=?, sales_tax=?, st_withheld=?, gross_value=?, it_withheld=?, net_payable=?
        WHERE id=?
        """
        vals = (
            rec["invoice_number"], rec["invoice_month"], rec["posting_date"], rec["client"], rec["ntn"], rec["authority"], 
            rec["category"], rec["subcategory"], rec["st_rate"], rec["st_registered"], 
            rec["atl_active"], rec["is_company"], rec["base_value"], rec["sales_tax"], 
            rec["st_withheld"], rec["gross_value"], rec["it_withheld"], rec["net_payable"],
            record_id
        )
        self.conn.execute(query, vals)
        self.conn.commit()

    def delete_invoice(self, record_id):
        self.conn.execute("DELETE FROM invoices WHERE id=?", (record_id,))
        self.conn.commit()

    def delete_all_invoices(self):
        self.conn.execute("DELETE FROM invoices")
        self.conn.commit()

    def fetch_all(self, search="", authority_filter="All", category_filter="All", month_filter="All", **kwargs):
        cursor = self.conn.cursor()
        query = "SELECT * FROM invoices WHERE 1=1"
        params = []

        if search:
            q = f"%{search}%"
            query += " AND (client LIKE ? OR invoice_number LIKE ? OR authority LIKE ? OR ntn LIKE ? OR invoice_month LIKE ?)"
            params.extend([q, q, q, q, q])

        if authority_filter and authority_filter != "All":
            query += " AND authority = ?"
            params.append(authority_filter)

        if category_filter and category_filter != "All":
            query += " AND category = ?"
            params.append(category_filter)

        if month_filter and month_filter != "All":
            query += " AND invoice_month = ?"
            params.append(month_filter)

        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def fetch_one(self, record_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id=?", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
