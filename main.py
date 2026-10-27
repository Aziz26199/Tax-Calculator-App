"""main.py - PyQt5 GUI for the Invoice Management & Tax Calculation System.

Run:  pip install PyQt5 openpyxl   (openpyxl only needed for .xlsx export)
      python main.py
"""
import sys
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget, QAbstractItemView,
)

import tax_logic as tl
from db_handler import DatabaseHandler, COLUMNS, HEADERS

MAX_AMT = 1e12


def money(v):
    return f"{v:,.2f}"


def amount_spin():
    s = QDoubleSpinBox()
    s.setRange(0, MAX_AMT)
    s.setDecimals(2)
    s.setGroupSeparatorShown(True)
    return s


# =====================================================================
class CalculatorTab(QWidget):
    def __init__(self, db, on_saved):
        super().__init__()
        self.db = db
        self.on_saved = on_saved
        self.editing_id = None
        self.result = None
        self._build()
        self._on_authority_changed()

    def _build(self):
        # ---- inputs ----
        self.inv_no = QLineEdit()
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.client = QLineEdit()
        self.authority = QComboBox()
        self.authority.addItems(tl.AUTHORITIES.keys())
        self.category = QComboBox()
        self.category.addItems(tl.CATEGORIES.keys())
        self.subcat = QComboBox()
        self.st_rate = QDoubleSpinBox()
        self.st_rate.setRange(0, 100)
        self.st_rate.setSuffix(" %")
        self.st_rate.setDecimals(2)
        self.chk_reg = QCheckBox("Service Provider ST Registered & Active?")
        self.chk_reg.setChecked(True)
        self.chk_atl = QCheckBox("Income Tax ATL Active?")
        self.chk_atl.setChecked(True)
        self.chk_co = QCheckBox("Service Provider is a Company?")
        self.chk_co.setChecked(True)
        self.base_in = amount_spin()
        self.chk_rev = QCheckBox("Reverse Working (Net Payment se nikalo)")
        self.net_in = amount_spin()
        self.net_in.setEnabled(False)

        form = QFormLayout()
        for label, w in [
            ("Invoice Number", self.inv_no), ("Date", self.date),
            ("Client Name", self.client), ("Tax Authority", self.authority),
            ("Category", self.category), ("Sub-Category", self.subcat),
            ("Sales Tax Rate", self.st_rate),
        ]:
            form.addRow(label, w)
        form.addRow(self.chk_reg)
        form.addRow(self.chk_atl)
        form.addRow(self.chk_co)
        form.addRow("Base Invoice Value", self.base_in)
        form.addRow(self.chk_rev)
        form.addRow("Net Payment Received", self.net_in)
        box_in = QGroupBox("Invoice Details")
        box_in.setLayout(form)

        # ---- results ----
        self.lbl = {}
        rform = QFormLayout()
        for key, text in [
            ("base", "Base Value"), ("st", "Sales Tax"),
            ("st_withheld", "ST Withheld"), ("gross", "Gross Invoice Value"),
            ("it_withheld", "Income Tax Withheld (Sec 153)"), ("net", "NET PAYABLE"),
        ]:
            l = QLabel("0.00")
            l.setAlignment(Qt.AlignRight)
            l.setStyleSheet("font-size:15px;")
            self.lbl[key] = l
            rform.addRow(text, l)
        self.lbl["net"].setStyleSheet("font-size:18px;font-weight:bold;color:#0a7a2f;")
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setStyleSheet("color:#555;")
        rform.addRow(self.info)
        box_out = QGroupBox("Results (live)")
        box_out.setLayout(rform)

        # ---- buttons ----
        self.btn_save = QPushButton("Save to Database")
        self.btn_clear = QPushButton("Clear / New")
        self.btn_save.clicked.connect(self.save)
        self.btn_clear.clicked.connect(self.clear)
        btns = QHBoxLayout()
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_clear)

        right = QVBoxLayout()
        right.addWidget(box_out)
        right.addLayout(btns)
        right.addStretch()

        root = QHBoxLayout(self)
        root.addWidget(box_in, 3)
        root.addLayout(right, 2)

        # ---- signals ----
        self.authority.currentTextChanged.connect(self._on_authority_changed)
        self.category.currentTextChanged.connect(self._on_category_changed)
        for w in (self.subcat,):
            w.currentTextChanged.connect(self.recalc)
        for w in (self.st_rate, self.base_in, self.net_in):
            w.valueChanged.connect(self.recalc)
        for w in (self.chk_reg, self.chk_atl, self.chk_co):
            w.toggled.connect(self.recalc)
        self.chk_rev.toggled.connect(self._on_reverse_toggled)
        self._on_category_changed(self.category.currentText())

    # ---------- handlers ----------
    def _on_authority_changed(self, *_):
        self.st_rate.blockSignals(True)
        self.st_rate.setValue(tl.default_st_rate(self.authority.currentText()) * 100)
        self.st_rate.blockSignals(False)
        self.recalc()

    def _on_category_changed(self, cat):
        self.subcat.blockSignals(True)
        self.subcat.clear()
        self.subcat.addItems(tl.CATEGORIES.get(cat, []))
        self.subcat.blockSignals(False)
        self.recalc()

    def _on_reverse_toggled(self, on):
        self.net_in.setEnabled(on)
        self.base_in.setEnabled(not on)
        self.recalc()

    def _params(self):
        return dict(
            authority=self.authority.currentText(),
            category=self.category.currentText(),
            subcategory=self.subcat.currentText(),
            st_registered=self.chk_reg.isChecked(),
            atl_active=self.chk_atl.isChecked(),
            is_company=self.chk_co.isChecked(),
            st_rate=self.st_rate.value() / 100.0,
        )

    def recalc(self, *_):
        if not self.subcat.currentText():
            return
        try:
            if self.chk_rev.isChecked():
                r = tl.reverse_gross_up(self.net_in.value(), **self._params())
                self.base_in.blockSignals(True)
                self.base_in.setValue(r["base"])
                self.base_in.blockSignals(False)
            else:
                r = tl.calculate(self.base_in.value(), **self._params())
        except ValueError as e:
            self.result = None
            self.info.setText(f"⚠ {e}")
            return
        self.result = r
        for k in ("base", "st", "st_withheld", "gross", "it_withheld", "net"):
            self.lbl[k].setText(money(r[k]))
        self.info.setText(
            f"ST rate {r['st_rate']*100:.2f}% | ST withheld {r['st_wh_frac']*100:.0f}% of ST | "
            f"IT rate {r['it_rate']*100:.2f}% on Gross"
        )

    def save(self):
        if not self.inv_no.text().strip() or not self.client.text().strip():
            QMessageBox.warning(self, "Missing", "Invoice Number aur Client Name zaroori hain.")
            return
        if not self.result or self.result["base"] <= 0:
            QMessageBox.warning(self, "Missing", "Valid amount enter karein.")
            return
        p, r = self._params(), self.result
        rec = {
            "invoice_number": self.inv_no.text().strip(),
            "date": self.date.date().toString("yyyy-MM-dd"),
            "client": self.client.text().strip(),
            "authority": p["authority"], "category": p["category"],
            "subcategory": p["subcategory"], "st_rate": p["st_rate"],
            "st_registered": int(p["st_registered"]), "atl_active": int(p["atl_active"]),
            "is_company": int(p["is_company"]),
            "base_value": round(r["base"], 2), "sales_tax": round(r["st"], 2),
            "st_withheld": round(r["st_withheld"], 2), "gross_value": round(r["gross"], 2),
            "it_withheld": round(r["it_withheld"], 2), "net_payable": round(r["net"], 2),
        }
        if self.editing_id:
            self.db.update_invoice(self.editing_id, rec)
            msg = "Invoice update ho gayi."
        else:
            self.db.insert_invoice(rec)
            msg = "Invoice save ho gayi."
        QMessageBox.information(self, "Done", msg)
        self.on_saved()
        self.clear()

    def clear(self):
        self.editing_id = None
        self.btn_save.setText("Save to Database")
        self.inv_no.clear()
        self.client.clear()
        self.date.setDate(QDate.currentDate())
        self.chk_rev.setChecked(False)
        self.base_in.setValue(0)
        self.net_in.setValue(0)
        self.recalc()

    def load_record(self, rec):
        """Load a saved invoice for editing."""
        self.editing_id = rec["id"]
        self.btn_save.setText("Update Invoice")
        self.chk_rev.setChecked(False)
        self.inv_no.setText(rec["invoice_number"])
        self.date.setDate(QDate.fromString(rec["date"], "yyyy-MM-dd"))
        self.client.setText(rec["client"])
        self.authority.blockSignals(True)
        self.authority.setCurrentText(rec["authority"])
        self.authority.blockSignals(False)
        self.category.setCurrentText(rec["category"])   # repopulates sub-categories
        self.subcat.setCurrentText(rec["subcategory"] or "")
        self.chk_reg.setChecked(bool(rec["st_registered"]))
        self.chk_atl.setChecked(bool(rec["atl_active"]))
        self.chk_co.setChecked(bool(rec["is_company"]))
        self.st_rate.setValue((rec["st_rate"] or 0) * 100)
        self.base_in.setValue(rec["base_value"])
        self.recalc()


# =====================================================================
class HistoryTab(QWidget):
    def __init__(self, db, on_edit):
        super().__init__()
        self.db = db
        self.on_edit = on_edit
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search client / invoice # / authority...")
        self.search.textChanged.connect(self.refresh)
        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.total_lbl = QLabel("")

        b_edit = QPushButton("Edit Selected")
        b_del = QPushButton("Delete Selected")
        b_exp = QPushButton("Export Excel / CSV")
        b_ref = QPushButton("Refresh")
        b_edit.clicked.connect(self.edit_selected)
        b_del.clicked.connect(self.delete_selected)
        b_exp.clicked.connect(self.export)
        b_ref.clicked.connect(self.refresh)
        bar = QHBoxLayout()
        for b in (b_edit, b_del, b_exp, b_ref):
            bar.addWidget(b)
        bar.addStretch()

        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(self.table)
        lay.addWidget(self.total_lbl)
        lay.addLayout(bar)
        self.refresh()

    def refresh(self, *_):
        rows = self.db.fetch_all(self.search.text().strip())
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, col in enumerate(COLUMNS):
                v = r[col]
                if col in ("st_registered", "atl_active", "is_company"):
                    v = "Yes" if v else "No"
                elif col == "st_rate":
                    v = f"{(v or 0)*100:.2f}%"
                elif isinstance(v, float):
                    v = money(v)
                item = QTableWidgetItem(str(v))
                if isinstance(r[col], float):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, j, item)
        self.total_lbl.setText(
            f"Records: {len(rows)}   |   Total Net Payable: {money(sum(r['net_payable'] for r in rows))}"
        )

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select", "Pehle koi row select karein.")
            return None
        return int(self.table.item(row, 0).text())

    def edit_selected(self):
        rid = self._selected_id()
        if rid:
            rec = self.db.fetch_one(rid)
            if rec:
                self.on_edit(rec)

    def delete_selected(self):
        rid = self._selected_id()
        if rid and QMessageBox.question(self, "Delete", "Kya aap ye record delete karna chahte hain?") \
                == QMessageBox.Yes:
            self.db.delete_invoice(rid)
            self.refresh()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export", "invoices.xlsx", "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        try:
            n = self.db.export(path)
            QMessageBox.information(self, "Exported", f"{n} records export ho gaye:\n{path}")
        except ImportError:
            QMessageBox.warning(self, "openpyxl missing",
                                "Excel ke liye `pip install openpyxl` karein, ya CSV choose karein.")


# =====================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Invoice Management & Tax Calculation System - Pakistan")
        self.resize(1200, 700)
        self.db = DatabaseHandler()
        self.tabs = QTabWidget()
        self.history = HistoryTab(self.db, self.edit_record)
        self.calc = CalculatorTab(self.db, self.history.refresh)
        self.tabs.addTab(self.calc, "Calculator && Entry")
        self.tabs.addTab(self.history, "Invoice History")
        self.setCentralWidget(self.tabs)

    def edit_record(self, rec):
        self.calc.load_record(rec)
        self.tabs.setCurrentIndex(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
