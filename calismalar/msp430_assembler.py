#!/usr/bin/env python3
"""
MSP430G253 için Basit Assembler & Qt Arayüzü (.obj Formatlı Çıktı)

Bu örnek, daha önce tanımladığımız basit assembler’ı PyQt5 ile grafiksel arayüz üzerinden kullanmanıza olanak sağlar.
Kullanıcı assembly kaynak kodunu düzenleyebilir, dosyadan açabilir, makine kodu (.obj) çıktısını görebilir ve kaydedebilir.
"""

import sys
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTextEdit, QVBoxLayout, QPushButton,
    QFileDialog, QLabel, QHBoxLayout
)

# --- Assembler Kodu ---

REGISTERS = {
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
    "R5": 5,
    "R6": 6,
    "R7": 7,
}

INSTRUCTIONS = {
    "MOV": {"opcode": 0x4000, "format": "reg_reg"},  # MOV src, dest
    "ADD": {"opcode": 0x5000, "format": "reg_reg"},  # ADD src, dest
    "SUB": {"opcode": 0x9000, "format": "reg_reg"},  # SUB src, dest
}

class Assembler:
    def __init__(self):
        self.symbol_table = {}  # Etiket tablosu
        self.machine_code = []  # (adres, kod) çiftleri
        self.lines = []         # Kaynak kod satırları

    def load_source(self, source_code):
        self.lines = source_code.splitlines()

    def preprocess_line(self, line):
        # Yorumları sil, boşlukları temizle.
        line = line.split(';')[0]
        return line.strip()

    def first_pass(self):
        """
        İlk geçiş: Etiketlerin adreslerini belirle.
        Her komutun 2 byte olduğunu varsayıyoruz.
        """
        address = 0
        for line in self.lines:
            line = self.preprocess_line(line)
            if not line:
                continue
            if line.endswith(':'):
                label = line[:-1].strip()
                self.symbol_table[label] = address
            else:
                address += 2

    def parse_operand(self, operand):
        """
        Operantı ayrıştırır: kayıt, sabit (immediate) veya etiket.
        """
        operand = operand.strip()
        if operand.upper() in REGISTERS:
            return ("register", REGISTERS[operand.upper()])
        elif operand.isdigit():
            return ("immediate", int(operand))
        elif operand.startswith("0x"):
            return ("immediate", int(operand, 16))
        else:
            return ("label", operand)

    def assemble_instruction(self, mnemonic, operands):
        if mnemonic not in INSTRUCTIONS:
            raise ValueError("Desteklenmeyen komut: " + mnemonic)
        instr_def = INSTRUCTIONS[mnemonic]
        opcode_base = instr_def["opcode"]

        # "reg_reg" formatında iki operant beklenir.
        if instr_def["format"] == "reg_reg":
            if len(operands) != 2:
                raise ValueError(mnemonic + " komutu 2 operant gerektirir")
            src_type, src_val = self.parse_operand(operands[0])
            dest_type, dest_val = self.parse_operand(operands[1])
            if src_type != "register" or dest_type != "register":
                raise ValueError(mnemonic + " komutu şu an yalnızca kayıt operantlarını destekler")
            # Örnek kodlama: opcode_base | (src_reg << 8) | (dest_reg << 4)
            code = opcode_base | (src_val << 8) | (dest_val << 4)
            return code
        else:
            raise ValueError("Desteklenmeyen format: " + mnemonic)

    def second_pass(self):
        address = 0
        for line in self.lines:
            line = self.preprocess_line(line)
            if not line:
                continue
            if line.endswith(':'):
                continue
            parts = re.split(r'\s+', line, maxsplit=1)
            mnemonic = parts[0].upper()
            operands = []
            if len(parts) > 1:
                operands = [op.strip() for op in parts[1].split(',')]
            code = self.assemble_instruction(mnemonic, operands)
            self.machine_code.append((address, code))
            address += 2

    def generate_output(self):
        output_lines = []
        for address, code in self.machine_code:
            output_lines.append(f"{address:04X}: {code:04X}")
        return "\n".join(output_lines)

    def assemble(self, source_code):
        self.load_source(source_code)
        self.first_pass()
        self.second_pass()
        return self.generate_output()

# --- Qt Arayüzü ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MSP430 Assembler - Qt Arayüzü (.obj Çıktısı)")

        # Ana widget ve layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout()

        # Assembly kaynak kodu düzenleme alanı
        self.source_label = QLabel("Assembly Kaynak Kodu:")
        self.source_edit = QTextEdit()
        self.layout.addWidget(self.source_label)
        self.layout.addWidget(self.source_edit)

        # Butonlar (Dosya Aç, Assemble Et, Çıktıyı Kaydet)
        self.button_layout = QHBoxLayout()

        self.open_button = QPushButton("Dosya Aç")
        self.open_button.clicked.connect(self.open_file)
        self.button_layout.addWidget(self.open_button)

        self.assemble_button = QPushButton("Assemble Et")
        self.assemble_button.clicked.connect(self.assemble_code)
        self.button_layout.addWidget(self.assemble_button)

        self.save_button = QPushButton("Çıktıyı Kaydet (.obj)")
        self.save_button.clicked.connect(self.save_output)
        self.button_layout.addWidget(self.save_button)

        self.layout.addLayout(self.button_layout)

        # Obj dosyası çıktısını gösteren alan
        self.output_label = QLabel("Obj Dosyası Çıktısı:")
        self.output_edit = QTextEdit()
        self.layout.addWidget(self.output_label)
        self.layout.addWidget(self.output_edit)

        self.main_widget.setLayout(self.layout)

    def open_file(self):
        options = QFileDialog.Options()
        # Assembly kaynak dosyalarını açmak için filtre (.asm tercih edilebilir)
        filename, _ = QFileDialog.getOpenFileName(self, "Assembly Kaynak Dosyasını Aç", "",
                                                  "Assembly Dosyaları (*.asm);;Tüm Dosyalar (*)", options=options)
        if filename:
            with open(filename, "r") as f:
                code = f.read()
                self.source_edit.setPlainText(code)

    def assemble_code(self):
        source_code = self.source_edit.toPlainText()
        assembler = Assembler()
        try:
            output = assembler.assemble(source_code)
            self.output_edit.setPlainText(output)
        except Exception as e:
            self.output_edit.setPlainText("Hata: " + str(e))

    def save_output(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self, "Obj Dosyasını Kaydet", "",
                                                  "Obj Dosyaları (*.obj);;Tüm Dosyalar (*)",
                                                  options=options)
        if filename:
            with open(filename, "w") as f:
                f.write(self.output_edit.toPlainText())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(600, 600)
    window.show()
    sys.exit(app.exec_())
