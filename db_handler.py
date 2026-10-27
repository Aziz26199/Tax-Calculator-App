import sqlite3
import pandas as pd

DB_FILE = "invoices.db"

COLUMNS = [
    "id", "invoice_number", "date", "client", "ntn", "authority", "category", 
    "subcategory", "st_rate", "st_registered", "atl_active", "is_company", 
    "base_value", "sales_tax", "st_withheld", "gross_value", "it_withheld", "net_payable"
]

HEADERS = [
    "ID", "Invoice #", "Date", "Client", "NTN / CNIC", "Authority", "Category", 
    "Sub-Category", "ST Rate", "ST Reg.", "ATL", "Company", 
    "Base Value", "Sales Tax", "ST Withheld", "Gross Value", "IT Withheld", "Net Payable"
]

class DatabaseHandler:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            date TEXT,
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
            invoice_number, date, client, ntn, authority, category, subcategory, 
            st_rate, st_registered, atl_active, is_company, 
            base_value, sales_tax, st_withheld, gross_value, it_withheld, net_payable
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        vals = (
            rec.get("invoice_number", ""), rec.get("date", ""), rec.get("client", ""), rec.get("ntn", ""), 
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
            invoice_number=?, date=?, client=?, ntn=?, authority=?, category=?, subcategory=?, 
            st_rate=?, st_registered=?, atl_active=?, is_company=?, 
            base_value=?, sales_tax=?, st_withheld=?, gross_value=?, it_withheld=?, net_payable=?
        WHERE id=?
        """
        vals = (
            rec["invoice_number"], rec["date"], rec["client"], rec["ntn"], rec["authority"], 
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

    def fetch_all(self, search=""):
        cursor = self.conn.cursor()
        if search:
            q = f"%{search}%"
            cursor.execute("SELECT * FROM invoices WHERE client LIKE ? OR invoice_number LIKE ? OR authority LIKE ? OR ntn LIKE ? ORDER BY id DESC", (q, q, q, q))
        else:
            cursor.execute("SELECT * FROM invoices ORDER BY id DESC")
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def fetch_one(self, record_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id=?", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def export(self, path):
        rows = self.fetch_all()
        df = pd.DataFrame(rows)
        if not df.empty:
            df.columns = HEADERS
        df.to_excel(path, index=False) if path.endswith(".xlsx") else df.to_csv(path, index=False)
        return len(rows)
