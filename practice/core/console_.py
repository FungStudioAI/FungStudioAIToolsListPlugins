from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread

class Console(QObject):
    call_console_signal = pyqtSignal(str, int)

    def __init__(self,console_callback):
        super().__init__()
        self.call_console_signal.connect(console_callback)

    def write(self, message, leve):
        self.call_console_signal.emit(message, leve)