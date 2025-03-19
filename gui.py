# gui.py - Gelişmiş ve koyu temalı assembler arayüzü

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QPlainTextEdit
import sys
from assembler import assemble

class AssemblerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Assembler GUI")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #2e2e2e;
                color: #f0f0f0;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
            QPlainTextEdit, QTextEdit {
                background-color: #3e3e3e;
                border: 1px solid #555;
            }
            QPushButton {
                background-color: #5a5a5a;
                border: 1px solid #444;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
            }
            QLabel {
                color: #f0f0f0;
            }
        """)

        # Ana layout, iki sütun: sol kod editörü, sağda sonuç ve hata ekranları
        main_layout = QHBoxLayout()

        # Sol sütun: Kod editörü ve derle butonu
        left_layout = QVBoxLayout()
        self.label_code = QLabel("Assembly Kodu:")
        left_layout.addWidget(self.label_code)
        self.text_code = QPlainTextEdit()
        self.text_code.setPlaceholderText("Kodu buraya yazınız...")
        left_layout.addWidget(self.text_code)
        self.button_assemble = QPushButton("Derle")
        self.button_assemble.clicked.connect(self.assemble_code)
        left_layout.addWidget(self.button_assemble)
        
        main_layout.addLayout(left_layout, 1)  # sol sütun esneklik kazansın

        # Sağ sütun: Üstte sonuçlar, altta hatalar
        right_layout = QVBoxLayout()
        self.label_result = QLabel("Makine Kodu:")
        right_layout.addWidget(self.label_result)
        self.text_result = QTextEdit()
        self.text_result.setReadOnly(True)
        right_layout.addWidget(self.text_result, 1)  # sonuç alanı genişleyebilsin
        
        self.label_errors = QLabel("Hatalar:")
        right_layout.addWidget(self.label_errors)
        self.text_errors = QTextEdit()
        self.text_errors.setReadOnly(True)
        right_layout.addWidget(self.text_errors, 1)
        
        main_layout.addLayout(right_layout, 1)
        
        self.setLayout(main_layout)
    
    def assemble_code(self):
        # Her derlemeden önce çıktıları temizle
        self.text_result.clear()
        self.text_errors.clear()

        assembly_code = self.text_code.toPlainText()
        machine_code, errors = assemble(assembly_code)
        self.text_result.setPlainText("\n".join(machine_code))
        self.text_errors.setPlainText("\n".join(errors))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = AssemblerGUI()
    gui.show()
    sys.exit(app.exec_())
