import os
import random
import time
import requests
import keyring
import threading

from PyQt5.QtCore import Qt
from plugin_interface import PluginInterface
from PyQt5.QtWidgets import QDialog, QPushButton, QFormLayout, QLineEdit, QLabel, \
    QTableWidget, QTableWidgetItem, QDateEdit, QTextEdit, QComboBox
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QDate
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QUrl
from plugins.practice.core import encrypt_aes_ecb
from plugins.practice.core.login import LoginManager
from plugins.practice.core.console_ import Console
from plugins.practice.core.asynch_signal_manager import AsynchSignalManager
from plugins.practice.core.qwen_driver import Qwen
from plugins.practice.core.weekreport import WeekReportManager




class Plugin(PluginInterface):

    def __init__(self):
        self.console = None
        self.AsynchSignalManager = None
        self.mainWindow = None
        self.lock = threading.Lock()
        self.dialog = None
        self.usr_info = None
        self.weekpaper_img = None
        self.weekpaper_img_index = 0
        self.weekpaper_img_paths = None
        self.students_table = None
        self.weekpapers_table = None
        self.edit_date = None
        self.weekpaper_edit = None
        self.comment_edit = None
        self.grade_cmbox = None
        self.current_name = None
        self.current_id = None
        # 初始化一个session对象，用于保持会话状态
        self.session = requests.session()
        self.WeekReportManager = None
        self.qwen = None
        self.api_key_edit = None
        self.combobox_mode = None

    def pluginName(self):
        return "顶岗实习助手 FSAI @qrs 316"

    def uiFilePath(self):
        # 返回插件UI文件的路径
        return os.path.join(os.path.dirname(__file__), 'ui/main.ui')

    def close(self):
        def asynchClose():
            self.console.write(f"正在尝试关闭 {self.pluginName()} 插件......", 1)
            self.AsynchSignalManager.closeAll()
            with self.lock:
                if self.dialog:
                    self.dialog.close()
                    self.dialog.deleteLater()
                self.dialog = None
            self.console.write(f"{self.pluginName()} 插件 关闭成功！", 0)
        close_th = threading.Thread(target=asynchClose)
        close_th.start()

    def setupUi(self, mainWindow):
        if self.dialog:
            self.dialog.setVisible(True)
            return
        self.mainWindow = mainWindow
        # 加载UI文件并设置为停靠窗口的内容
        self.dialog = QDialog()  # 根据你的UI文件选择合适的基类
        uic.loadUi(self.uiFilePath(), self.dialog)

        # mainWindow.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.mainWindow.main_ui.form_layout.setWidget(1, QtWidgets.QFormLayout.SpanningRole, self.dialog)
        self.api_key_edit = self.dialog.findChild(QLineEdit, 'edit_api_key')
        # 获取API密钥
        api_key = keyring.get_password("practice", "@qrs316")
        if self.api_key_edit and api_key != "":
            self.api_key_edit.setText(api_key)
            self.console.write(f"API_KEY读取成功！", 0)

        def api_key_change(text):
            if text != "":
                # 设置API密钥
                keyring.set_password("practice", "@qrs316", f"{text}")
                self.console.write(f"API_KEY保存成功！", 0)

        self.api_key_edit.textChanged.connect(api_key_change)

        self.combobox_mode = self.dialog.findChild(QComboBox, 'comboBox_auto_mode')
        # 查找UI文件中的按钮并连接点击事件
        button_login = self.dialog.findChild(QPushButton, 'btn_login')
        button_login.clicked.connect(lambda: self.onButtonClicked('login'))
        button_pull = self.dialog.findChild(QPushButton, 'btn_pull')
        button_pull.clicked.connect(lambda: self.onButtonClicked('pull'))
        button_submit = self.dialog.findChild(QPushButton, 'btn_submit')
        button_submit.clicked.connect(lambda: self.onButtonClicked('submit'))
        button_img_next = self.dialog.findChild(QPushButton, 'btn_next_img')
        button_img_next.clicked.connect(lambda: self.onButtonClicked('img_next'))
        button_ai_tipc = self.dialog.findChild(QPushButton, 'btn_ai_tipc')
        button_ai_tipc.clicked.connect(lambda: self.onButtonClicked('ai_tipc'))
        button_redo = self.dialog.findChild(QPushButton, 'btn_redo')
        button_redo.clicked.connect(lambda: self.onButtonClicked('redo'))
        button_create_call = self.dialog.findChild(QPushButton, 'btn_create_call')
        button_create_call.clicked.connect(lambda: self.onButtonClicked('create_@'))
        button_auto_all = self.dialog.findChild(QPushButton, 'btn_auto_all')
        button_auto_all.clicked.connect(lambda: self.onButtonClicked('auto_all'))
        self.weekpaper_edit = self.dialog.findChild(QTextEdit, 'edit_weekpaper')
        self.comment_edit = self.dialog.findChild(QTextEdit, 'edit_comment')
        self.grade_cmbox = self.dialog.findChild(QComboBox, 'comboBox_grade')
        self.usr_info = self.dialog.findChild(QLabel, "label_usr_info")
        self.weekpaper_img = self.dialog.findChild(QLabel, "label_img")
        self.students_table = self.dialog.findChild(QTableWidget, "table_students")
        self.students_table.cellClicked.connect(lambda row, col: self.onTableClicked(row, col, 'students'))
        self.weekpapers_table = self.dialog.findChild(QTableWidget, "table_weekpapers")
        self.weekpapers_table.cellClicked.connect(lambda row, col: self.onTableClicked(row, col, 'weekpapers'))
        self.edit_date = self.dialog.findChild(QDateEdit, "edit_date")
        self.edit_date.setDate(QDate.currentDate())  # 设置为当前系统日期
        self.edit_date.setCalendarPopup(True)  # 显示日历弹出窗口，方便选择日期

    def initialize(self, console_callback):
        self.imgDownManager = QNetworkAccessManager()
        self.imgDownManager.finished.connect(self.on_img_download_finished)
        self.console = Console(console_callback)
        self.AsynchSignalManager = AsynchSignalManager()
        self.AsynchSignalManager.call_uiUpdate_signal.connect(self.uiUpDateCallback)
        self.AsynchSignalManager.call_event_change_signal.connect(self.eventChangeCallback)
        self.WeekReportManager = WeekReportManager(self.console,self.lock,self.AsynchSignalManager)
        self.qwen = Qwen(self.console,self.lock)
        self.console.write(f"{self.pluginName()} 插件初始化成功。账号密码为湖南汽车工程职业大学的账号密码。在使用AI功能进行周报评审前，请先正确填写API_URL链接、"
                           f"API_KEY密钥和模型名称。如果使用通义千问做为AI语言模型接入，API_URL默认为 https://dashscope.aliyuncs.com/compatible-mode/v1，"
                           f"模型默认为qwen-max，API_KEY请进入通义千问阿里的官网生成，并将其复制到API_KEY编辑框里即可使用AI功能。请在阿里官网中关注token的使用量，以免产生不必要的费用。", 0)

    def invisible(self):
        if self.dialog:
            self.dialog.setVisible(False)
            item = self.mainWindow.main_ui.form_layout.itemAt(1, QFormLayout.FieldRole)
            self.mainWindow.main_ui.form_layout.removeItem(item)  # 从布局中移除该项

    def onTableClicked(self, row, column, arg):
        # 获取当前点击行的所有数据
        current_row_data = []
        try:
            self.weekpaper_edit.setText("")
            self.comment_edit.setText("")
            self.grade_cmbox.setCurrentIndex(0)
            self.weekpaper_img_index = 0
            self.weekpaper_img_paths = None
            self.weekpaper_img.setPixmap(QPixmap())
            if arg == "students":
                self.weekpapers_table.setRowCount(0)
                self.current_name = self.students_table.item(row, 1).text()
                self.current_id = None
                pull_th = threading.Thread(target=self.WeekReportManager.pullWeekpapers, 
                                           args=(self.session, 
                                                 self.students_table.item(row, 6).text(), 
                                                 self.students_table.item(row, 7).text(), 
                                                 self.students_table.item(row, 1).text()))
                pull_th.start()
            elif arg == "weekpapers":             
                self.current_id = self.weekpapers_table.item(row, 3).text()
                pull_th = threading.Thread(target=self.WeekReportManager.pullWeekpaperContent, 
                                           args=(True,self.session, 
                                                 self.weekpapers_table.item(row, 3).text(),
                                                 self.current_name))
                pull_th.start()
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)

    def onButtonClicked(self, args):
        try:
            if args == "login":
                edit_usr = self.dialog.findChild(QLineEdit, 'edit_usr')
                edit_psw = self.dialog.findChild(QLineEdit, 'edit_psw')
                if str(edit_usr.text()).strip() != '' and str(edit_psw.text()).strip() != '':
                    key = "c6dda3852e2d4be2"  # 密钥必须是16字节长
                    password = encrypt_aes_ecb.encode(key, edit_psw.text())
                    loginManager = LoginManager(self.lock,self.mainWindow,self.console,self.AsynchSignalManager)
                    send_th = threading.Thread(target=loginManager.login, 
                                               args=(self.session, edit_usr.text(), password))
                    send_th.start()
                else:
                    self.console.write("请输入合适的账号和密码！", 1)
            elif args == "pull":
                date = self.edit_date.date()
                year = date.year()
                pull_th = threading.Thread(target=self.WeekReportManager.pullStudents, args=(self.session,year))
                pull_th.start()
            elif args == "submit":
                data = (self.comment_edit.toPlainText(), self.grade_cmbox.currentIndex() + 1)
                pull_th = threading.Thread(target=self.WeekReportManager.weekpaperReviewSubmit,
                                           args=(self.session, self.current_id, data, self.current_name))
                pull_th.start()
            elif args == "redo":
                redo_th = threading.Thread(target=self.WeekReportManager.weekpaperRedo,
                                           args=(self.session, self.current_id, self.current_name))
                redo_th.start()
            elif args == "img_next":
                if self.weekpaper_img_paths:
                    if self.weekpaper_img_index >= len(self.weekpaper_img_paths):
                        self.weekpaper_img_index = 0                   
                    request =  QNetworkRequest(QUrl(self.weekpaper_img_paths[self.weekpaper_img_index]))
                    self.imgDownManager.get(request)
            elif args == "create_@":
                row_count = self.students_table.rowCount()
                result = "\n"
                for row in range(row_count):
                    # 使用 item() 方法获取单元格中的 QTableWidgetItem
                    name = self.students_table.item(row, 1).text().strip()
                    week_report_num = self.students_table.item(row, 3).text()
                    week_report_writed = self.students_table.item(row, 4).text()
                    incomplete = int(week_report_num) - int(week_report_writed)
                    if incomplete == int(week_report_num):
                        result = result + f"@{name} 应写周报{week_report_num}篇，目前为止一篇都没有完成！请抓紧时间完成。\n"
                    elif incomplete > 0:
                        result = result + f"@{name} 应写周报{week_report_num}篇，目前只完成{week_report_writed}篇，还差{incomplete}篇，请抓紧时间完成。\n"
                self.console.write(result + "大家务必引起重视，顶岗实习分数是毕业设计的一部分，占比40%，大家务必引起重视！",0)
            elif args == "auto_all":
                auto_th = threading.Thread(target=self.auto_review)
                auto_th.start()
            elif args == "ai_tipc":
                if self.weekpaper_edit.toPlainText().strip() == "":
                    self.console.write(f"没有问题内容！", 1)
                    return
                self.console.write(f"正在思考中......", 0)
                question = (f"{self.weekpaper_edit.toPlainText()}。这是高职学生的顶岗实习内容和心得，给出50到150字评语，回答一些与实习内容相关的内容，比如提到的人和事，"
                            f"并针对性的给学生一个建议和方向，并给出优良中的一个等级，优的机率小一点。以json形式返回结果，前后不要多余的符号，关键字为评语和等级。")
                edit_api_url = self.dialog.findChild(QLineEdit, 'edit_api_url')
                edit_api_key = self.dialog.findChild(QLineEdit, 'edit_api_key')
                edit_api_model = self.dialog.findChild(QLineEdit, 'edit_api_model')
                def question_callback(anser):
                    if anser:
                        self.AsynchSignalManager.call_uiUpdate_signal.emit("ai_tipc", (anser['评语'],anser['等级']))
                        self.console.write(anser['评语'], 0)
                question_th = threading.Thread(target=self.qwen.get,
                                               args=(edit_api_url.text(),edit_api_key.text(),
                                                     edit_api_model.text(),question,question_callback))
                question_th.start()
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)

    def eventChangeCallback(self, event, msg):
        if event in ["logining","pulling"]:
            self.students_table.setRowCount(0)
            self.weekpapers_table.setRowCount(0)
            self.weekpaper_edit.setText("")
            self.comment_edit.setText("")
            self.grade_cmbox.setCurrentIndex(0)
            self.weekpaper_img.setPixmap(QPixmap())
            self.weekpaper_img_index = 0
            self.weekpaper_img_paths = None
            self.current_name = None
            self.current_id = None
        elif event == "logined":
            if msg[0] == True:
                date = self.edit_date.date()
                year = date.year()
                pull_th = threading.Thread(target=self.WeekReportManager.pullStudents, args=(self.session,year))
                pull_th.start()
        elif event == "auto_click_table":
            self.onTableClicked(msg[0],0,msg[1])
        elif event == "auto_click_ai_tipc":
            self.onButtonClicked("ai_tipc")
        elif event == "auto_click_submit":
            self.onButtonClicked("submit")
        
    def uiUpDateCallback(self, event, msg):
        if event == "user":
            if self.usr_info:
                self.usr_info.setText(msg[0])
        elif event == "students":
            if self.students_table:
                # 获取当前表格的行数
                current_row_count = self.students_table.rowCount()
                # 插入新行
                self.students_table.insertRow(current_row_count)
                # 为每一列设置数据
                for col, value in enumerate(msg):
                    item = QTableWidgetItem(value)
                    self.students_table.setItem(current_row_count, col, item)
        elif event == "weekpapers":
            if self.weekpapers_table:
                # 获取当前表格的行数
                current_row_count = self.weekpapers_table.rowCount()
                # 插入新行
                self.weekpapers_table.insertRow(current_row_count)
                # 为每一列设置数据
                for col, value in enumerate(msg):
                    item = QTableWidgetItem(value)
                    self.weekpapers_table.setItem(current_row_count, col, item)
        elif event == "weekpaper_content":
            if self.weekpaper_edit and self.comment_edit and self.grade_cmbox:
                self.weekpaper_edit.setText(f"实习内容：\n {msg[0]} \n  实习心得：\n {msg[1]} \n")
                self.comment_edit.setText(msg[3])
                if msg[4] != '':
                    self.grade_cmbox.setCurrentIndex(int(msg[4]) - 1)
                else:
                    self.grade_cmbox.setCurrentIndex(0)
        elif event == "weekpaper_img":
            self.weekpaper_img_paths = msg
            request =  QNetworkRequest(QUrl(msg[0]))
            self.imgDownManager.get(request)
        elif event == "ai_tipc":
            self.comment_edit.setText(msg[0])
            grade = {"优":1,"良":2,"中":3}
            self.grade_cmbox.setCurrentIndex(grade.get(msg[1]) - 1)
        elif event == "reset_wkpr_table":
            if self.weekpapers_table:
                self.weekpapers_table.setRowCount(0)

    def on_img_download_finished(self, reply: QNetworkReply):
        try:
            if reply.error() == QNetworkReply.NoError:
                pixmap = QPixmap()
                pixmap.loadFromData(reply.readAll())
                self.weekpaper_img.setPixmap(pixmap.scaled(self.weekpaper_img.size(), aspectRatioMode=Qt.IgnoreAspectRatio))  # 调整图片大小以适应QLabel
                self.weekpaper_img_index = self.weekpaper_img_index + 1
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)
        finally:
            reply.deleteLater()

    def auto_review(self):
        comments = ["该生在实习期间严格遵守公司的各项规章制度，工作态度认真负责，能够快速适应新的工作环境。积极参与团队合作，主动学习新知识，展现了良好的职业素养。",
                    "实习过程中，该同学表现出色，对业务的理解能力较强，能独立完成分配的任务。与同事相处融洽，善于沟通，体现了较强的团队协作精神和解决问题的能力。",
                    "在实习期间，该生不仅掌握了专业技能，还学会了如何高效地管理时间。面对挑战时保持积极乐观的态度，勇于尝试并成功解决了一系列实际问题。",
                    "这位同学在实习中展示了优秀的自学能力和实践操作技巧。无论是日常工作还是特别项目，都能够按时高质量地完成任务，并获得了同事们的高度评价。",
                    "实习期内，该生展现出了极强的责任心和敬业精神。对待工作任务一丝不苟，注重细节，在短时间内成长为团队不可或缺的一员。",
                    "该实习生具有很强的学习欲望和技术敏感度，能迅速掌握新技术并应用于实践中。同时，他/她也乐于分享自己的见解，促进了团队内部的知识交流。",
                    "该同学在工作中表现出了高度的专业性，对待客户耐心细致，服务意识强。通过努力提升自我，为公司带来了正面的影响。",
                    "实习期间，该生积极参与各类培训活动，不断提升个人能力。其扎实的专业基础加上勤奋好学的精神使得他在众多实习生中脱颖而出。",
                    "该实习生在实习期间展现了出色的领导潜力，能够有效组织团队成员共同完成任务。他/她的创新思维为项目带来了新的视角。",
                    "该生在实习过程中始终保持谦虚谨慎的工作态度，善于倾听他人意见，从而不断完善自我。这种态度帮助他在短时间内取得了显著进步。",
                    "在整个实习阶段，该生始终以高标准要求自己，努力克服困难，不断追求卓越。他/她的努力得到了大家的认可，是值得信赖的伙伴。",
                    "该实习生不仅拥有扎实的专业知识，还具备良好的人际交往能力。无论是在处理复杂事务还是日常交流中都表现得游刃有余。",
                    "实习期间，该生积极参加企业组织的各项活动，增强了自身的综合素质。他/她的热情和活力感染了周围的人，营造了积极向上的工作氛围。",
                    "该同学在实习期间充分展示了自己的才华，特别是在数据分析方面表现突出。他/她的洞察力为决策提供了有力支持。",
                    "该实习生在工作中表现出极大的耐心和细心，确保每一项任务都能准确无误地完成。他/她的严谨作风赢得了同事们的一致好评。",
                    "实习期间，该生展现了出色的时间管理和任务规划能力，总能在规定时间内高效完成任务。这体现了他/她高度的责任感。",
                    "该同学在实习中展现出强烈的求知欲，总是寻找机会学习新事物。他/她的好奇心促使他/她在专业领域不断深入探索。",
                    "该实习生在实习期间积累了丰富的实战经验，提高了自身的技术水平。他/她的成长轨迹清晰可见，未来发展前景广阔。",
                    "该生在实习过程中始终保持积极主动的态度，遇到问题时敢于提出自己的看法，并积极参与讨论寻求解决方案。",
                    "实习期内，该生展示了优秀的沟通协调能力，能够有效地与不同部门进行对接。他/她的桥梁作用大大提高了工作效率。",
                    "该实习生在实习期间注重理论联系实际，将课堂上学到的知识灵活运用到工作中去。这种做法极大地提升了他/她的实战能力。",
                    "该同学在实习中表现出了强烈的责任心和使命感，愿意承担更多的责任。他/她的付出对公司的发展做出了重要贡献。",
                    "实习期间，该生凭借扎实的专业知识和过硬的技术实力解决了多个难题。他/她的专业精神令人钦佩。",
                    "该实习生在实习过程中展现出了极高的情商，能够在压力下保持冷静，妥善处理人际关系。这是他/她的一大优势。",
                    "该生在实习期间不仅完成了本职工作，还积极参与了额外项目的开发。他/她的多面手特质让他/她在团队中扮演了重要角色。",
                    "实习期内，该生始终保持着对工作的热情，即使面对枯燥的任务也能全身心投入。这种态度使他/她成为团队中的榜样。",
                    "该同学在实习中展示了出色的抗压能力，即便在高强度的工作环境下也能保持高效的工作状态。他/她的坚韧不拔值得称赞。",
                    "该实习生在实习期间展现了强大的执行力，对于上级安排的任务总能迅速响应并执行到位。他/她的行动力令人印象深刻。",
                    "实习期间，该生积极参与团队建设活动，增进了与同事之间的了解和信任。他/她的亲和力让整个团队更加团结。",
                    "该同学在实习过程中展现了卓越的问题解决能力，能够独立思考并找到有效的解决方案。他/她的智慧和勇气让人敬佩。",
                    "该实习生在实习期间注重细节，对每一个环节都进行了精心打磨。他/她的精益求精精神保证了工作的高品质。",
                    "实习期内，该生展现了出色的创新能力，提出了多项改进建议并被采纳实施。他/她的创造性思维为公司注入了新的活力。",
                    "该同学在实习中表现出了很强的适应能力，能够迅速融入新环境并发挥作用。他/她的灵活性使他/她很快成为了团队的重要成员。",
                    "该实习生在实习期间展现了出色的文字表达能力，撰写的各种文档逻辑清晰、条理分明。他/她的写作才能得到了广泛认可。",
                    "实习期间，该生注重自我反思和总结，每次完成任务后都会仔细回顾过程中的得失。他/她的自我提升意识非常强烈。",
                    "该同学在实习过程中展示了良好的职业道德，始终坚守诚信原则。他/她的正直品质赢得了大家的尊重。",
                    "该实习生在实习期间积极参与各种技能培训，不断提升自己的职业技能。他/她的进取心让他/她在竞争中占据优势。",
                    "实习期内，该生展现了出色的客户服务意识，对待每一位顾客都充满热情。他/她的优质服务态度给客户留下了深刻印象。",
                    "该同学在实习中表现出了很强的计划性和前瞻性，能够提前预见可能出现的问题并做好准备。他/她的预判能力让人刮目相看。",
                    "该实习生在实习期间展现了优秀的资源管理能力，能够合理调配人力物力资源。他/她的统筹能力对项目的顺利推进起到了关键作用。",
                    "实习期间，该生展现了良好的情绪管理能力，即使遇到挫折也能保持积极的心态。他/她的心理韧性是他/她成功的秘诀之一。",
                    "该同学在实习过程中展示了出色的跨文化交际能力，能够与来自不同背景的人顺畅交流。他/她的开放心态让他/她更具竞争力。",
                    "该实习生在实习期间展现了强大的数据分析能力，能够从大量数据中提取有价值的信息。他/她的分析能力为决策提供了依据。",
                    "实习期内，该生展现了出色的应急处理能力，能够在突发事件发生时迅速作出反应。他/她的应变能力令人佩服。",]
        grades = ["优","良","中"]
        try:
            self.dialog.setEnabled(False)
            self.AsynchSignalManager.call_event_change_signal.emit("logined",(True,))
            time.sleep(0.5)
            with self.lock:
                time.sleep(1)
            students_row_count = self.students_table.rowCount()
            for row in range(students_row_count):
                week_report_no_review = int(self.students_table.item(row, 5).text())
                if week_report_no_review == 0:
                    continue
                self.AsynchSignalManager.call_event_change_signal.emit("auto_click_table",(row,"students"))
                time.sleep(0.5)
                with self.lock:
                    time.sleep(1)
                report_row_count = self.weekpapers_table.rowCount()
                for row1 in range(report_row_count):
                    if self.weekpapers_table.item(row1, 0).text() == "未提交":
                        break
                    if self.weekpapers_table.item(row1, 2).text().strip() != "未评":
                        continue
                    self.AsynchSignalManager.call_event_change_signal.emit("auto_click_table",(row1,"weekpapers"))
                    time.sleep(0.5)
                    with self.lock:
                        time.sleep(1)
                    if self.combobox_mode.currentIndex() == 0:
                        self.AsynchSignalManager.call_event_change_signal.emit("auto_click_ai_tipc",(row1,))
                    else:
                        num = random.randrange(0, 50)
                        grade = random.randrange(0, 3)
                        self.AsynchSignalManager.call_uiUpdate_signal.emit("ai_tipc",(comments[num],grades[grade]))
                    time.sleep(0.5)
                    with self.lock:
                        time.sleep(1)
                    self.AsynchSignalManager.call_event_change_signal.emit("auto_click_submit",(row1,))
                    time.sleep(0.5)
                    with self.lock:
                        time.sleep(1)
            self.AsynchSignalManager.call_event_change_signal.emit("logined",(True,))
            time.sleep(0.5)
            with self.lock:
                time.sleep(1)
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)
        finally:
            self.dialog.setEnabled(True)
    
