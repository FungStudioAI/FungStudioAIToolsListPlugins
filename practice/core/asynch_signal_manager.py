from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread

class AsynchSignalManager(QObject):
    call_uiUpdate_signal = pyqtSignal(str, tuple)
    call_event_change_signal = pyqtSignal(str, tuple)

    def closeAll(self):
        try:
            self.call_uiUpdate_signal.disconnect()
            self.call_event_change_signal.disconnect()
        except Exception as e:
            pass