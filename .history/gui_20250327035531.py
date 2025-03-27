import sys
import importlib.util
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPlainTextEdit, QPushButton, QLabel, QFileDialog
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter
from PyQt5.QtCore import Qt

# 21g.py dosyasını dinamik olarak içe aktarma
spec = importlib.util.spec_from_file_location("msp430_assembler", "assembler.py")
msp430_assembler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(msp430_assembler)

# Syntax Highlighter
class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.format = QTextCharFormat()
        self.format.setForeground(QColor("lightgreen"))
        self.format.setFontWeight(QFont.Bold)
    
    def highlightBlock(self, text):
        keywords = ["MOV", "ADD", "SUB", "JMP", "CALL", "RET", "NOP", "ADDC", 
                    "SUBC", "CMP", "DADD", "BIT", "BIC", "BIS", "XOR", "AND", 
                    "RRC", "SWPB", "RRA", "SXT", "PUSH", "JNE", "JEQ", "JNC", 
                    "JC", "JN", "JGE", "JL", "JMP", "START", "END", ".DATA", 
                    ".CODE", ".ORG"]
        for word in keywords:
            if word in text:
                self.setFormat(text.index(word), len(word), self.format)

# Ana GUI sınıfı
class AssemblerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("MSP430 Assembler")
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
                color: #f0f0f0;
                padding: 10px;
            }
            QPushButton {
                background-color: #5a5a5a;
                border: 1px solid #444;
                padding: 10px;
                color: #f0f0f0;
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
        self.highlighter = Highlighter(self.text_code.document())
        
        self.button_assemble = QPushButton("Derle")
        self.button_assemble.clicked.connect(self.assemble_code)
        left_layout.addWidget(self.button_assemble)
        
        self.save_button = QPushButton("Kaydet")
        self.save_button.clicked.connect(self.save_code)
        left_layout.addWidget(self.save_button)

        self.load_button = QPushButton("Yükle")
        self.load_button.clicked.connect(self.load_code)
        left_layout.addWidget(self.load_button)
        
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
        msp430_assembler.SYMTAB.clear()

        assembly_code = self.text_code.toPlainText()
        object_code, errors = self.assemble(assembly_code)
        self.text_result.setPlainText(object_code)
        self.text_errors.setPlainText(errors)
    
    def assemble(self, assembly_code):
        msp430_assembler.pass1(assembly_code)
        if msp430_assembler.errors:
            return "", "\n".join(msp430_assembler.errors)
        msp430_assembler.pass2()
        output = "\n".join([f"ADDR: {format(loc, 'X')} | HEX: {format(code, 'X')} | BIN: {bin(code)[2:].zfill(16)}" for loc, code in msp430_assembler.object_code])
        msp430_assembler.save_object_code("output.hex")
        return output, ""
    
    def save_code(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Kod Kaydet", "", "Assembly Files (*.asm);;All Files (*)")
        if filename:
            with open(filename, "w") as file:
                file.write(self.text_code.toPlainText())
    
    def load_code(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Kod Yükle", "", "Assembly Files (*.asm);;All Files (*)")
        if filename:
            with open(filename, "r") as file:
                self.text_code.setPlainText(file.read())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = AssemblerGUI()
    gui.show()
    sys.exit(app.exec_())
