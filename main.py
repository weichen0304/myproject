import sys
import sqlite3
# 匯出 .ics 需要的函式庫
from ics import Calendar, Event
from datetime import datetime
# 時區功能需要的函式庫
try:
    import pytz
except ImportError:
    print("錯誤：缺少 'pytz' 函式庫。")
    print("請在終端機執行: python.exe -m pip install pytz")
    sys.exit()

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QCalendarWidget, QListWidget, QDialog, QLabel, QLineEdit,
    QTextEdit, QTimeEdit, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QMessageBox,
    QCheckBox,  # 鬧鐘功能需要
    QFileDialog # 匯出 .ics 功能需要
)
from PyQt6.QtCore import QDate, QTimer, QDateTime, QTime, Qt

DB = "calendar_schedule.db"

def init_db():
    """初始化資料庫 (無變動)"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, date TEXT, start_time TEXT, end_time TEXT, description TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT, teacher TEXT, classroom TEXT,
        weekday INTEGER, start_period INTEGER, end_period INTEGER
    )''')

    try:
        c.execute("SELECT set_alarm, alarm_triggered FROM events LIMIT 1")
    except sqlite3.OperationalError:
        print("為 'events' 表新增鬧鐘欄位...")
        c.execute("ALTER TABLE events ADD COLUMN set_alarm INTEGER DEFAULT 0")
        c.execute("ALTER TABLE events ADD COLUMN alarm_triggered INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


# ---------------- 新增事件對話框 (v5 版, 已修正) ----------------
class AddEventDialog(QDialog):
    def __init__(self, date):
        super().__init__()
        self.setWindowTitle(f"新增事件 - {date}")
        self.date = date
        self.title_edit = QLineEdit()
        self.start_time = QTimeEdit()
        self.end_time = QTimeEdit()
        self.desc_edit = QTextEdit()
        self.alarm_check = QCheckBox("⏰ 設定鬧鐘提醒")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("事件標題："))
        layout.addWidget(self.title_edit)
        layout.addWidget(QLabel("開始時間："))
        layout.addWidget(self.start_time)
        layout.addWidget(QLabel("結束時間："))
        layout.addWidget(self.end_time)
        layout.addWidget(QLabel("描述："))
        layout.addWidget(self.desc_edit)
        layout.addWidget(self.alarm_check)
        save_btn = QPushButton("儲存")
        save_btn.clicked.connect(self.save_event)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def save_event(self):
        """[已修正] 儲存時間強制使用 "HH:mm:ss" 標準格式"""
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "錯誤", "請輸入事件標題!")
            return
        
        set_alarm = 1 if self.alarm_check.isChecked() else 0
        start_time_str = self.start_time.time().toString("HH:mm:ss")
        end_time_str = self.end_time.time().toString("HH:mm:ss")

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''INSERT INTO events(title, date, start_time, end_time, description, set_alarm)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                  (title, self.date, start_time_str, end_time_str,
                   self.desc_edit.toPlainText(), set_alarm))
        conn.commit()
        conn.close()
        self.accept()


# ---------------- 新增課程對話框 (無變動) ----------------
class AddCourseDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("新增課程")
        self.resize(300, 250)
        self.name_edit = QLineEdit()
        self.teacher_edit = QLineEdit()
        self.room_edit = QLineEdit()
        self.weekday_box = QComboBox()
        self.weekday_box.addItems(["週一", "週二", "週三", "週四", "週五"])
        self.start_period = QSpinBox()
        self.start_period.setRange(1, 10)
        self.end_period = QSpinBox()
        self.end_period.setRange(1, 10)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("課程名稱："))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("教師："))
        layout.addWidget(self.teacher_edit)
        layout.addWidget(QLabel("教室："))
        layout.addWidget(self.room_edit)
        layout.addWidget(QLabel("星期："))
        layout.addWidget(self.weekday_box)
        layout.addWidget(QLabel("節次（起-迄）："))
        layout.addWidget(self.start_period)
        layout.addWidget(self.end_period)
        save_btn = QPushButton("儲存")
        save_btn.clicked.connect(self.save_course)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def save_course(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "錯誤", "請輸入課程名稱！")
            return
        weekday = self.weekday_box.currentIndex() + 1
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''INSERT INTO courses(course_name, teacher, classroom, weekday, start_period, end_period)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                  (name, self.teacher_edit.text(), self.room_edit.text(), weekday,
                   self.start_period.value(), self.end_period.value()))
        conn.commit()
        conn.close()
        self.accept()


# ---------------- 主介面 (v5 版, 已加入刪除功能) ----------------
class CalendarScheduleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("行事曆與課表系統 (PyQt6)")
        self.resize(850, 550)
        self.calendar = QCalendarWidget()
        self.calendar.selectionChanged.connect(self.show_events)
        self.event_list = QListWidget()
        self.add_event_btn = QPushButton("新增事件")
        self.add_course_btn = QPushButton("新增課程")
        self.view_schedule_btn = QPushButton("查看課表")
        self.delete_event_btn = QPushButton("刪除事件") # [已新增]
        self.export_btn = QPushButton("匯出日曆 (.ics)")
        self.add_event_btn.clicked.connect(self.add_event)
        self.add_course_btn.clicked.connect(self.add_course)
        self.view_schedule_btn.clicked.connect(self.show_schedule)
        self.delete_event_btn.clicked.connect(self.delete_event) # [已新增]
        self.export_btn.clicked.connect(self.export_to_ics)
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.event_list)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_event_btn)
        btn_layout.addWidget(self.delete_event_btn) # [已新增]
        btn_layout.addWidget(self.add_course_btn)
        btn_layout.addWidget(self.view_schedule_btn)
        right_layout.addLayout(btn_layout)
        right_layout.addWidget(self.export_btn) 
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.calendar, 2)
        main_layout.addLayout(right_layout, 3)
        self.setLayout(main_layout)
        self.alarm_timer = QTimer(self)
        self.alarm_timer.timeout.connect(self.check_alarms)
        self.alarm_timer.start(30000)
        self.show_events()
        self.check_alarms()

    def show_events(self):
        """[已修改] 顯示事件時，儲存 'id' 以便刪除"""
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        weekday = self.calendar.selectedDate().dayOfWeek()
        self.event_list.clear()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT course_name, classroom, start_period, end_period FROM courses WHERE weekday=?", (weekday,))
        courses = c.fetchall()
        if courses:
            self.event_list.addItem("📚 今日課程：")
            for course in courses:
                self.event_list.addItem(f"{course[0]} @ {course[1]}（第{course[2]}~{course[3]}節）")
        else:
            self.event_list.addItem("📚 今日無課程")
        self.event_list.addItem("────────────────────────")
        self.event_list.addItem("🗓️ 今日事件：")
        
        # [修改] 查詢時多選 'id' 欄位
        c.execute("SELECT id, title, start_time, end_time, set_alarm FROM events WHERE date=?", (date,))
        events = c.fetchall()
        if events:
            for e in events:
                # e[0] = id, e[1] = title, e[2] = start, e[3] = end, e[4] = alarm
                alarm_icon = " ⏰" if e[4] == 1 else ""
                display_text = f"{e[1]} ({e[2]}~{e[3]}){alarm_icon}"
                item = QListWidgetItem(display_text)
                # [關鍵] 將 'id' (e[0]) 儲存在這個 item 裡面
                item.setData(Qt.ItemDataRole.UserRole, e[0])
                self.event_list.addItem(item)
        else:
            self.event_list.addItem("無事件")
        conn.close()

    def add_event(self):
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        dialog = AddEventDialog(date)
        if dialog.exec():
            self.show_events()

    def delete_event(self):
        """[已新增] 刪除在 QListWidget 中當前選擇的事件"""
        current_item = self.event_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "錯誤", "請先在列表中選擇一個要刪除的「事件」。")
            return
        event_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not event_id:
            QMessageBox.warning(self, "錯誤", "您選擇的項目不是一個可刪除的事件。")
            return
            
        reply = QMessageBox.question(
            self, "確認刪除", f"您確定要刪除這個事件嗎？\n\n{current_item.text().strip()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                c.execute("DELETE FROM events WHERE id = ?", (event_id,))
                conn.commit()
                conn.close()
                self.show_events()
            except Exception as e:
                QMessageBox.critical(self, "資料庫錯誤", f"刪除失敗：\n{e}")

    def add_course(self):
        dialog = AddCourseDialog()
        if dialog.exec():
            self.show_events()

    def show_schedule(self):
        self.schedule_window = ScheduleWindow()
        self.schedule_window.show()

    def check_alarms(self):
        """鬧鐘檢查 (無變動)"""
        print(f"檢查鬧鐘: {QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')}")
        now = QDateTime.currentDateTime()
        current_date_str = now.toString("yyyy-MM-dd")
        current_time_str = now.toString("HH:mm")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''SELECT id, title FROM events 
                     WHERE date = ? AND start_time = ? AND 
                     set_alarm = 1 AND alarm_triggered = 0''',
                  (current_date_str, current_time_str))
        alarms_to_trigger = c.fetchall()
        if alarms_to_trigger:
            for event_id, title in alarms_to_trigger:
                print(f"觸發鬧鐘 (ID: {event_id}): {title}")
                QMessageBox.information(self, "⏰ 鬧鐘提醒 ⏰", 
                                        f"事件時間到了：\n\n** {title} **")
                c.execute("UPDATE events SET alarm_triggered = 1 WHERE id = ?", (event_id,))
            conn.commit()
        conn.close()

    # --- [ *** 終極修正版 v6 *** ] ---
    def export_to_ics(self):
        """
        匯出 .ics 檔案
        (修正時區 + 修正 AM/PM 解析 + [修正] Android 的 UID 錯誤)
        """
        
        try:
            local_tz = pytz.timezone("Asia/Taipei")
        except pytz.UnknownTimeZoneError:
            QMessageBox.critical(self, "錯誤", "無法載入 'Asia/Taipei' 時區資訊。")
            return

        # 1. 另存新檔
        save_path, _ = QFileDialog.getSaveFileName(
            self, "儲存 iCalendar 檔案", "MyEvents.ics", "iCalendar 檔案 (*.ics)"
        )
        if not save_path:
            return

        # 2. 讀取資料庫
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        # --- [v6 修正] --- 我們需要 'id' 來建立安全的 UID
        c.execute("SELECT id, title, date, start_time, end_time, description FROM events")
        db_events = c.fetchall()
        conn.close()
        
        # 3. 建立 Calendar 物件
        cal = Calendar()
        parse_errors = 0 
        
        # --- [v6 修正] --- 新增 event_id 變數
        for event_id, title, date, start_time, end_time, description in db_events:
            dt_start, dt_end = None, None
            try:
                start_str_orig = f"{date} {start_time}"
                end_str_orig = f"{date} {end_time}"
                
                dt_start_naive, dt_end_naive = None, None
                
                # (v5 修正) 處理 AM/PM 和 24小時制
                if "上午" in start_str_orig or "下午" in start_str_orig:
                    start_is_pm = "下午" in start_str_orig
                    end_is_pm = "下午" in end_str_orig
                    start_str_clean = start_str_orig.replace("上午", "").replace("下午", "").strip()
                    end_str_clean = end_str_orig.replace("上午", "").replace("下午", "").strip()
                    try:
                        dt_start_naive = datetime.strptime(start_str_clean, "%Y-%m-%d %I:%M:%S")
                        dt_end_naive = datetime.strptime(end_str_clean, "%Y-%m-%d %I:%M:%S")
                    except ValueError:
                        dt_start_naive = datetime.strptime(start_str_clean, "%Y-%m-%d %I:%M")
                        dt_end_naive = datetime.strptime(end_str_clean, "%Y-%m-%d %I:%M")
                    if start_is_pm and dt_start_naive.hour < 12: dt_start_naive = dt_start_naive.replace(hour=dt_start_naive.hour + 12)
                    if end_is_pm and dt_end_naive.hour < 12: dt_end_naive = dt_end_naive.replace(hour=dt_end_naive.hour + 12)
                    if not start_is_pm and dt_start_naive.hour == 12: dt_start_naive = dt_start_naive.replace(hour=0)
                    if not end_is_pm and dt_end_naive.hour == 12: dt_end_naive = dt_end_naive.replace(hour=0)
                else:
                    try:
                        dt_start_naive = datetime.strptime(start_str_orig, "%Y-%m-%d %H:%M:%S")
                        dt_end_naive = datetime.strptime(end_str_orig, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        dt_start_naive = datetime.strptime(start_str_orig, "%Y-%m-%d %H:%M")
                        dt_end_naive = datetime.strptime(end_str_orig, "%Y-%m-%d %H:%M")
                
                dt_start = local_tz.localize(dt_start_naive)
                dt_end = local_tz.localize(dt_end_naive)
                
                if dt_end <= dt_start:
                    print(f"跳過無效事件 (結束時間早於開始): {title}")
                    parse_errors += 1
                    continue

                # 建立 Event 物件
                e = Event()
                e.name = title
                e.begin = dt_start
                e.end = dt_end
                e.description = description
                
                # --- [v6 終極修正] ---
                # 手動設定一個 "安全" 的 UID，Android 系統才不會拒絕
                # 我們使用資料庫的 id 確保它是獨一無二的
                e.uid = f"my-calendar-event-{event_id}@example.com"
                # --- [修正完畢] ---

                cal.events.add(e)
                
            except ValueError as ve:
                parse_errors += 1
                print(f"錯誤：無法解析日期/時間格式 {start_str_orig} - {ve}")
            except Exception as ex:
                parse_errors += 1
                print(f"建立事件時發生未知錯誤: {ex}")

        # 4. 寫入檔案 (無變動)
        if not cal.events and parse_errors == 0:
            QMessageBox.warning(self, "注意", "資料庫中沒有可匯出的事件。")
            return
            
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.writelines(cal.serialize_iter())
            
            if parse_errors > 0:
                QMessageBox.warning(self, "完成 (有錯誤)", 
                                   f"日曆已匯出，但有 {parse_errors} 個事件因格式錯誤而跳過。")
            else:
                QMessageBox.information(self, "成功", f"日曆已成功匯出至：\n{save_path}")
                
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"匯出失敗：\n{e}")


# ---------------- 課表視窗 (無變動) ----------------
class ScheduleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("課表檢視")
        self.resize(700, 400)
        self.table = QTableWidget(10, 5)
        self.table.setHorizontalHeaderLabels(["週一", "週二", "週三", "週四", "週五"])
        self.table.setVerticalHeaderLabels([f"第{i}節" for i in range(1, 11)])
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_courses()

    def load_courses(self):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT course_name, classroom, weekday, start_period, end_period FROM courses")
        for name, room, wd, sp, ep in c.fetchall():
            for p in range(sp, ep + 1):
                item = QTableWidgetItem(f"{name}\n@{room}")
                self.table.setItem(p - 1, wd - 1, item)
        conn.close()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QListWidgetItem
    
    init_db()
    app = QApplication(sys.argv)
    win = CalendarScheduleApp()
    win.show()
    sys.exit(app.exec())