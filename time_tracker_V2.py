from __future__ import annotations
import sys, csv
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QPalette, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QSpacerItem,
    QSizePolicy, QDoubleSpinBox, QDateEdit
)

# ---------- storage format ----------
ISO_FMT = "%Y-%m-%dT%H:%M:%S"  # CSV format

@dataclass
class Punch:
    in_time: datetime
    out_time: Optional[datetime] = None

    def duration(self) -> timedelta:
        end = self.out_time or datetime.now()
        return max(end - self.in_time, timedelta(0))

def round_to_six_minutes(td: timedelta) -> timedelta:
    """Round to nearest 6 minutes (0.1h) half-up, per punch."""
    secs = max(0, int(td.total_seconds()))
    inc = 6 * 60
    rounded = (secs + inc // 2) // inc
    return timedelta(seconds=rounded * inc)

class TimeTrackerState:
    def __init__(self) -> None:
        self.punches: List[Punch] = []

    @property
    def is_clocked_in(self) -> bool:
        return bool(self.punches and self.punches[-1].out_time is None)

    def clock_in(self) -> None:
        if self.is_clocked_in:
            raise RuntimeError("Already clocked in.")
        self.punches.append(Punch(in_time=datetime.now()))

    def clock_out(self) -> None:
        if not self.is_clocked_in:
            raise RuntimeError("Not currently clocked in.")
        self.punches[-1].out_time = datetime.now()

    # ---- CSV ----
    def load_csv(self, path: Path) -> None:
        if not path.exists():
            return
        out: List[Punch] = []
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    tin = datetime.strptime(row["in_time"], ISO_FMT)
                    tout = datetime.strptime(row["out_time"], ISO_FMT) if (row.get("out_time") or "").strip() else None
                    out.append(Punch(tin, tout))
                except Exception:
                    # skip malformed lines
                    continue
        self.punches = out

    def save_csv(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["in_time", "out_time"])
            w.writeheader()
            for p in self.punches:
                w.writerow({
                    "in_time": p.in_time.strftime(ISO_FMT),
                    "out_time": p.out_time.strftime(ISO_FMT) if p.out_time else ""
                })
        tmp.replace(path)

# ---------- UI ----------
def qdate_to_date(qd: QDate) -> date:
    return date(qd.year(), qd.month(), qd.day())

class TimeTracker(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sar's Time Tracker - BeepBoop")
        self.setMinimumSize(720, 480)
        self.setWindowIcon(QIcon())

        self.data_path = Path(__file__).with_name("time_tracker_data.csv")
        self.state = TimeTrackerState()
        self.state.load_csv(self.data_path)

        self._build_ui()
        self._apply_dark()
        self._wire()
        self._start_timers()
        self._refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Header: title + clock
        head = QHBoxLayout()
        title = QLabel("Sar's Time Tracker - BeepBoop")
        title.setStyleSheet("font-size:22px; font-weight:600;")
        head.addWidget(title)
        head.addItem(QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum))
        self.clock_label = QLabel("--:--:--")
        self.clock_label.setStyleSheet("font-family:monospace; font-size:16px;")
        head.addWidget(self.clock_label)
        root.addLayout(head)

        # Controls row: start/end + wage + pay
        ctr = QHBoxLayout()
        ctr.addWidget(QLabel("From:"))
        self.start_date = QDateEdit(calendarPopup=True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addDays(-6))  # default last 7 days
        ctr.addWidget(self.start_date)

        ctr.addWidget(QLabel("To:"))
        self.end_date = QDateEdit(calendarPopup=True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        ctr.addWidget(self.end_date)

        ctr.addItem(QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum))

        ctr.addWidget(QLabel("Wage:"))
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setPrefix("$")
        self.rate_input.setDecimals(2)
        self.rate_input.setRange(0.0, 1000.0)
        self.rate_input.setSingleStep(0.25)
        self.rate_input.setValue(20.00)
        ctr.addWidget(self.rate_input)

        self.pay_label = QLabel("Pay (rounded): $0.00")
        self.pay_label.setStyleSheet("font-size:15px; font-weight:600; margin-left:8px;")
        ctr.addWidget(self.pay_label)

        root.addLayout(ctr)

        # Status + buttons
        act = QHBoxLayout()
        self.status_label = QLabel("Status: Not clocked in")
        act.addWidget(self.status_label)
        act.addItem(QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum))
        self.btn_in = QPushButton("Clock In")
        self.btn_out = QPushButton("Clock Out")
        for b in (self.btn_in, self.btn_out):
            b.setFixedHeight(36)
            b.setCursor(Qt.PointingHandCursor)
        act.addWidget(self.btn_in)
        act.addWidget(self.btn_out)
        root.addLayout(act)

        # Table (simple)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "In", "Out", "Rounded h (0.1h)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table)

        # Totals
        foot = QHBoxLayout()
        self.rounding_hint = QLabel("Rounding: per punch, nearest 6 minutes (0.1h).")
        self.rounding_hint.setStyleSheet("font-size:12px; color:#aaa;")
        foot.addWidget(self.rounding_hint)
        foot.addItem(QSpacerItem(20,20,QSizePolicy.Expanding,QSizePolicy.Minimum))
        self.total_label = QLabel("Total hours (rounded): 0.0")
        self.total_label.setStyleSheet("font-size:14px;")
        foot.addWidget(self.total_label)
        root.addLayout(foot)

    def _apply_dark(self) -> None:
        pal = QPalette()
        base = QColor(30,30,30); alt = QColor(45,45,45); text = QColor(230,230,230); accent = QColor(70,120,255)
        pal.setColor(QPalette.Window, base)
        pal.setColor(QPalette.WindowText, text)
        pal.setColor(QPalette.Base, QColor(25,25,25))
        pal.setColor(QPalette.AlternateBase, alt)
        pal.setColor(QPalette.Text, text)
        pal.setColor(QPalette.Button, alt)
        pal.setColor(QPalette.ButtonText, text)
        pal.setColor(QPalette.Highlight, accent)
        pal.setColor(QPalette.HighlightedText, QColor(255,255,255))
        self.setPalette(pal)
        self.setStyleSheet("""
            QWidget { color:#E6E6E6; }
            QPushButton { border:1px solid #3A3A3A; border-radius:8px; padding:6px 12px; background:#2C2C2C; }
            QPushButton:hover { background:#383838; }
            QPushButton:disabled { color:#888; }
            QHeaderView::section { background:#2C2C2C; border:0; padding:8px; font-weight:600; }
            QTableWidget { gridline-color:#444; }
        """)
        QApplication.setStyle("Fusion")

    def _wire(self) -> None:
        self.btn_in.clicked.connect(self.on_in)
        self.btn_out.clicked.connect(self.on_out)
        self.start_date.dateChanged.connect(self._refresh)
        self.end_date.dateChanged.connect(self._refresh)
        self.rate_input.valueChanged.connect(self._refresh_footer_only)

    def _start_timers(self) -> None:
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._tick)
        self.clock_timer.start(250)

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._refresh_footer_only)
        self.ui_timer.start(1000)

    # ---- slots ----
    def on_in(self) -> None:
        try:
            self.state.clock_in()
            self.state.save_csv(self.data_path)
        except RuntimeError as e:
            QMessageBox.warning(self, "Already Clocked In", str(e))
        self._refresh()

    def on_out(self) -> None:
        try:
            self.state.clock_out()
            self.state.save_csv(self.data_path)
        except RuntimeError as e:
            QMessageBox.warning(self, "Not Clocked In", str(e))
        self._refresh()

    def _tick(self) -> None:
        self.clock_label.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))

    # ---- helpers ----
    def _punches_in_range(self, start_d: date, end_d: date) -> List[Punch]:
        if start_d > end_d:
            start_d, end_d = end_d, start_d
        return [p for p in self.state.punches if start_d <= p.in_time.date() <= end_d]

    # ---- refresh ----
    def _refresh(self) -> None:
        self.btn_in.setEnabled(not self.state.is_clocked_in)
        self.btn_out.setEnabled(self.state.is_clocked_in)
        self.status_label.setText("Status: ✅ Clocked In" if self.state.is_clocked_in else "Status: ⏹ Not clocked in")
        self._populate_table()
        self._refresh_footer_only()

    def _populate_table(self) -> None:
        start_d = qdate_to_date(self.start_date.date())
        end_d = qdate_to_date(self.end_date.date())
        punches = self._punches_in_range(start_d, end_d)
        punches.sort(key=lambda p: (p.in_time, p.out_time or datetime.max))

        self.table.setRowCount(0)
        for p in punches:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p.in_time.strftime("%Y-%m-%d")))
            self.table.setItem(row, 1, QTableWidgetItem(p.in_time.strftime("%H:%M:%S")))
            self.table.setItem(row, 2, QTableWidgetItem(p.out_time.strftime("%H:%M:%S") if p.out_time else "— (running)"))
            r_hours = round_to_six_minutes(p.duration()).total_seconds() / 3600.0
            self.table.setItem(row, 3, QTableWidgetItem(f"{r_hours:.1f}"))
            for c in range(4):
                it = self.table.item(row, c)
                if it:
                    it.setTextAlignment(Qt.AlignCenter)

    def _refresh_footer_only(self) -> None:
        start_d = qdate_to_date(self.start_date.date())
        end_d = qdate_to_date(self.end_date.date())
        punches = self._punches_in_range(start_d, end_d)

        total_rounded = timedelta(0)
        for p in punches:
            total_rounded += round_to_six_minutes(p.duration())

        hours = total_rounded.total_seconds() / 3600.0
        self.total_label.setText(f"Total hours (rounded): {hours:.1f}")

        wage = float(self.rate_input.value())
        pay = hours * wage
        self.pay_label.setText(f"Pay (rounded): ${pay:,.2f}")

    # save on close
    def closeEvent(self, e) -> None:  # noqa: N802
        try:
            self.state.save_csv(self.data_path)
        finally:
            super().closeEvent(e)

def main():
    app = QApplication(sys.argv)
    w = TimeTracker()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
