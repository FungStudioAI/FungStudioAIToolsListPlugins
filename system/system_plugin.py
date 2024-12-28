from PyQt5.QtCore import Qt, pyqtSignal, QObject
from plugin_interface import PluginInterface
from PyQt5.QtWidgets import QAction, QDockWidget, QWidget, QDialog, QPushButton, QFormLayout
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import os


class Console(QObject):
    call_console_signal = pyqtSignal(str, int)

    def connect_callback(self, console_callback):
        self.call_console_signal.connect(console_callback)

    def write(self, message, leve):
        self.call_console_signal.emit(message, leve)


class Plugin(PluginInterface):

    def __init__(self):
        self.console = None
        self.mainWindow = None
        self.dock_widget = None
        self.dialog = None

    def pluginName(self):
        return "System"

    def uiFilePath(self):
        # 返回插件UI文件的路径
        return os.path.join(os.path.dirname(__file__), 'ui/system_plugin_main.ui')
    
    def close(self):
        self.dock_widget.close()
        item = self.mainWindow.main_ui.form_layout.itemAt(1, QFormLayout.FieldRole)
        self.mainWindow.main_ui.form_layout.removeItem(item)  # 从布局中移除该项

    def setupUi(self, mainWindow):
        # 创建一个新的停靠窗口（Dock Widget）
        self.dock_widget = QDockWidget("System Plugin", self.mainWindow)
        # mainWindow.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.mainWindow.main_ui.form_layout.setWidget(1, QtWidgets.QFormLayout.SpanningRole, self.dock_widget)

        # 加载UI文件并设置为停靠窗口的内容
        self.dialog = QDialog()  # 根据你的UI文件选择合适的基类
        uic.loadUi(self.uiFilePath(), self.dialog)
        self.dock_widget.setWidget(self.dialog)

        # 查找UI文件中的按钮并连接点击事件
        self.findButtonsAndConnectSignals()

        # 添加动作到主窗口的菜单
        action = QAction("Toggle Example Plugin", self.mainWindow)
        self.mainWindow.menuExtras.addAction(action)
        action.triggered.connect(self.toggleVisibility)

    def initialize(self, mainWindow, console_callback):
        self.mainWindow = mainWindow
        self.console = Console()
        self.console.connect_callback(console_callback)
        self.console.write(f"{self.pluginName()} 插件初始化成功", 0)

    def toggleVisibility(self):
        if self.dock_widget:
            self.dock_widget.setVisible(not self.dock_widget.isVisible())

    def findButtonsAndConnectSignals(self):
        # 假设你有一个名为 pushButtonExample 的按钮
        button_example = self.dialog.findChild(QPushButton, 'dialog_btn_ok')
        if button_example is not None:
            button_example.clicked.connect(self.onButtonClicked)

    def onButtonClicked(self):
        self.console.write("Button in the plugin was clicked!", 0)
        # 在这里添加你想要执行的逻辑
