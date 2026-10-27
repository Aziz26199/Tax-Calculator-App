"""db_handler.py - SQLite storage for the Invoice Management & Tax Calculation System."""
import csv
import sqlite3

DB_FILE = "invoices.db"

COLUMNS = [
    "id", "invoice_number", "date", "client", "authority", "category",
    "subcategory", "st_rate", "st_registered", "atl_active", "is_company",
    "base_value", "sales_tax", "st_withheld", "gross_value",
    "it_withheld", "net_payable",
]

HEADERS = [
    "ID", "Invoice #", "Date", "Client", "Authority", "Category",
    "Sub-Category", "ST Rate", "ST Reg.", "ATL", "Company",
    "Base Value", "Sales Tax", "ST Withheld", "Gross Value",
    "IT Withheld", "Net Payable",
]


class DatabaseHandler:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self._create_table()

    def _connect(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_table(self):
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT NOT NULL,
                    date TEXT NOT NULL,
                    client TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    st_rate REAL,
                    st_registered INTEGER,
                    atl_active INTEGER,
                    is_company INTEGER,
                    base_value REAL NOT NULL,
                    sales_tax REAL NOT NULL,
                    st_withheld REAL NOT NULL,
                    gross_value REAL NOT NULL,
                    it_withheld REAL NOT NULL,
                    net_payable REAL NOT NULL
                )"""
            )

    # ---------- CRUD ----------
    def insert_invoice(self, d):
        cols = COLUMNS[1:]
        sql = f"INSERT INTO invoices ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
        with self._connect() as conn:
            return conn.execute(sql, [d[c] for c in cols]).lastrowid

    def update_invoice(self, invoice_id, d):
        cols = COLUMNS[1:]
        sql = f"UPDATE invoices SET {','.join(c + '=?' for c in cols)} WHERE id=?"
        with self._connect() as conn:
            conn.execute(sql, [d[c] for c in cols] + [invoice_id])

    def delete_invoice(self, invoice_id):
        with self._connect() as conn:
            conn.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))

    def fetch_all(self, search=""):
        sql = "SELECT * FROM invoices"
        params = []
        if search:
            sql += " WHERE client LIKE ? OR invoice_number LIKE ? OR authority LIKE ?"
            params = [f"%{search}%"] * 3
        sql += " ORDER BY date DESC, id DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def fetch_one(self, invoice_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
            return dict(row) if row else None

    # ---------- Export ----------
    def export(self, path):
        """Export to .xlsx (needs openpyxl) or .csv depending on extension."""
        rows = self.fetch_all()
        data = [[r[c] for c in COLUMNS] for r in rows]
        if path.lower().endswith(".xlsx"):
            from openpyxl import Workbook  # pip install openpyxl
            wb = Workbook()
            ws = wb.active
            ws.title = "Invoices"
            ws.append(HEADERS)
            for row in data:
                ws.append(row)
            wb.save(path)
        else:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(HEADERS)
                w.writerows(data)
        return len(data)
