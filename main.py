import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QCalendarWidget, QLabel, QPushButton,
    QGroupBox, QTimeEdit, QMessageBox,
    QSplitter, QInputDialog
)
from PyQt6.QtCore import (
    QDate, Qt, QLocale, 
    QTimer, QTime, QDateTime
)
from PyQt6.QtGui import QFont, QColor

class ScheduleCalendarApp(QMainWindow):
    """
    行事曆與課表查詢系統主視窗
    包含日曆、事件、鬧鐘功能、可調整版面及按鈕互動。
    """
    def __init__(self):
        super().__init__()
        
        # --- 應用程式狀態 (資料儲存) ---
        self.alarms = [] # 儲存鬧鐘列表: [(QDate, QTime, description), ...]
        self.events = {} # 使用字典儲存事件 {QDate: [(名稱, 描述), ...], ...}
        
        # 視窗設定
        self.setWindowTitle("行事曆與課表查詢系統 (PyQt6)")
        self.setGeometry(100, 100, 850, 600)
        
        # 設置主中央 Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # --- 1. 創建左側日曆容器 ---
        self.left_widget = QWidget()
        calendar_container = QVBoxLayout(self.left_widget)
        
        # 日曆控件初始化
        self.calendar = QCalendarWidget(self.left_widget)
        self.calendar.setLocale(QLocale(QLocale.Language.Chinese, QLocale.Country.Taiwan))
        self.calendar.setGridVisible(True)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setCurrentPage(2025, 11) 
        self.calendar.setStyleSheet(self._get_calendar_stylesheet())
        self.calendar.clicked.connect(self.update_event_display)
        
        calendar_container.addWidget(self.calendar)
        
        # --- 2. 創建右側事件/鬧鐘容器 ---
        self.right_widget = QWidget()
        right_vbox = QVBoxLayout(self.right_widget)
        
        # 2a. 鬧鐘設定區
        alarm_group = QGroupBox("設定鬧鐘")
        alarm_layout = QHBoxLayout(alarm_group)
        
        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm") 
        self.time_input.setMinimumHeight(30)
        
        btn_set_alarm = QPushButton("設定鬧鐘")
        btn_set_alarm.setMinimumHeight(30)
        btn_set_alarm.clicked.connect(self.set_alarm) 
        
        alarm_layout.addWidget(self.time_input)
        alarm_layout.addWidget(btn_set_alarm)
        right_vbox.addWidget(alarm_group)
        
        # 2b. 今日課表/事件 顯示區
        current_date_str = QDate.currentDate().toString("yyyy年M月d日")
        self.event_group = QGroupBox(f"{current_date_str} 課表")
        self.event_group.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        
        event_layout = QVBoxLayout(self.event_group)
        self.event_label = QLabel("今日事件：\n無事件")
        self.event_label.setFont(QFont("Microsoft YaHei", 10))
        self.event_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        event_layout.addWidget(self.event_label)
        right_vbox.addWidget(self.event_group)
        
        # 2c. 底部按鈕區
        right_vbox.addStretch(1) # 推擠按鈕到底部
        button_hbox = QHBoxLayout()
        
        btn_add_event = QPushButton("新增事件")
        btn_add_class = QPushButton("新增課程")
        btn_view_schedule = QPushButton("查詢課表")
        
        btn_add_event.setMinimumHeight(35)
        btn_add_class.setMinimumHeight(35)
        btn_view_schedule.setMinimumHeight(35)

        # *** 連接按鈕事件到方法 (此版本：事件和課程連接到終端機輸出，排除彈窗問題) ***
        btn_add_event.clicked.connect(self.add_event_clicked) 
        btn_add_class.clicked.connect(self.add_class_clicked) 
        btn_view_schedule.clicked.connect(self.view_schedule_clicked)
        # **************************************************************************
        
        button_hbox.addWidget(btn_add_event)
        button_hbox.addWidget(btn_add_class)
        button_hbox.addWidget(btn_view_schedule)
        right_vbox.addLayout(button_hbox)

        # --- 3. 使用 QSplitter 整合實現版面調整 ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal) # 水平分割
        self.splitter.addWidget(self.left_widget)
        self.splitter.addWidget(self.right_widget)
        self.splitter.setSizes([550, 300]) 

        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(self.splitter)
        
        # --- 4. 啟動 QTimer 鬧鐘檢查器 ---
        self.update_event_display(QDate.currentDate()) 
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_alarms)
        self.timer.start(1000)

    def _get_calendar_stylesheet(self):
        """用於設定日曆的樣式表 (CSS)"""
        return """
            QCalendarWidget QAbstractItemView:enabled {
                selection-background-color: #0078D7;
                selection-color: white;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: black;
            }
            #qt_calendar_navigationbar {
                background-color: #0078D7;
                color: white;
            }
            #qt_calendar_prevmonth, #qt_calendar_nextmonth, 
            #qt_calendar_monthbutton, #qt_calendar_yearbutton {
                color: white;
            }
        """

    # --- 關鍵修正：將新增事件和課程改為終端機輸出 ---
    def add_event_clicked(self):
        """處理「新增事件」：檢查連接並彈出輸入框"""
        print("--- 新增事件按鈕被點擊！(檢查連接成功) ---")
        
        selected_date = self.calendar.selectedDate()
        event_name, ok = QInputDialog.getText(
            self, 
            f"新增事件 - {selected_date.toString('yyyy年M月d日')}", 
            "請輸入事件名稱："
        )
        
        if ok and event_name:
            description = ""
            if selected_date not in self.events:
                self.events[selected_date] = []
            
            self.events[selected_date].append((event_name, description))
            self.update_event_display(selected_date)
            
            QMessageBox.information(
                self, 
                "事件已新增", 
                f"已在 {selected_date.toString('yyyy/MM/dd')} 新增事件：{event_name}"
            )
        elif ok:
             QMessageBox.warning(self, "輸入錯誤", "事件名稱不能為空。")

    def add_class_clicked(self):
        """處理「新增課程」：檢查連接 (終端機輸出)"""
        print("--- 新增課程按鈕被點擊！(檢查連接成功) ---")
        QMessageBox.information(self, "功能提示", "您點擊了「新增課程」。\n此功能通常需要使用 QDialog 進行多欄位輸入。")

    def view_schedule_clicked(self):
        """處理「查詢課表」按鈕點擊事件"""
        print("--- 查詢課表按鈕被點擊！---")
        QMessageBox.information(self, "功能提示", "您點擊了「查詢課表」。")
    # -----------------------------------------------------

    def update_event_display(self, date: QDate):
        """根據選定的日期更新右側的事件/課表顯示。"""
        date_str = date.toString("yyyy年M月d日") 
        
        events_on_day = self.events.get(date, [])
        
        if events_on_day:
            event_lines = [f"- {name}" for name, desc in events_on_day]
            event_text = "今日事件：\n" + "\n".join(event_lines)
        elif date == QDate(2025, 11, 1):
             event_text = "今日事件：\n- 軟體工程期中報告\n- 專題討論會 (下午)"
        else:
            event_text = "今日事件：\n無事件"

        alarms_today = [
            f"- 鬧鐘 {time.toString('HH:mm')} ({desc})" 
            for date_obj, time, desc in self.alarms 
            if date_obj == date
        ]
        
        if alarms_today:
            event_text += "\n\n當日鬧鐘：\n" + "\n".join(alarms_today)
        
        self.event_group.setTitle(f"{date_str} 課表")
        self.event_label.setText(event_text)

    def set_alarm(self):
        """設定鬧鐘"""
        selected_date = self.calendar.selectedDate()
        selected_time = self.time_input.time()
        
        now = QDateTime.currentDateTime()
        alarm_datetime = QDateTime(selected_date, selected_time)

        if alarm_datetime <= now:
            QMessageBox.warning(self, "設定錯誤", "請設定未來的時間作為鬧鐘。")
            return

        description = "設定的提醒事項" 
        self.alarms.append((selected_date, selected_time, description))
        
        self.update_event_display(selected_date) 
        
        QMessageBox.information(
            self, 
            "鬧鐘已設定", 
            f"鬧鐘已設定於:\n日期: {selected_date.toString('yyyy/MM/dd')}\n時間: {selected_time.toString('HH:mm')}"
        )

    def check_alarms(self):
        """每秒被 QTimer 呼叫，檢查是否有鬧鐘時間到達"""
        now_date = QDate.currentDate()
        now_time = QTime.currentTime()
        current_minute = now_time.toString("HH:mm")

        triggered_alarms_indices = []
        
        for i, (alarm_date, alarm_time, desc) in enumerate(self.alarms):
            alarm_minute = alarm_time.toString("HH:mm")

            if alarm_date == now_date and alarm_minute == current_minute:
                triggered_alarms_indices.append(i) 
                
                QMessageBox.critical(
                    self, 
                    "🔔 鬧鐘響了！", 
                    f"時間到：{current_minute}！\n提醒事項：{desc}"
                )
        
        for index in sorted(triggered_alarms_indices, reverse=True):
            del self.alarms[index]
            
        if triggered_alarms_indices and self.calendar.selectedDate() == now_date:
            self.update_event_display(now_date)


if __name__ == '__main__':
    # 這是啟動 PyQt 應用程式的標準程式碼
    app = QApplication(sys.argv)
    window = ScheduleCalendarApp()
    window.show()
    sys.exit(app.exec())
    