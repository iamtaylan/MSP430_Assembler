#!/usr/bin/env python3
"""
Basitleştirilmiş MSP430 Assembler (Genişletilmiş Opcode seti + START ve .DATA direktifleri)
Üç aşamalı işleyiş:
  1. Pass: Sembol tablosu oluşturma ve direktifleri işleme (START, .DATA)
  2. Pass: Makine kodu üretimi
  3. Çıktı üretimi
"""

# Sembol tablosu
SYMTAB = {}

# OPCODE tanımları – 4-bit alan olarak düşünülüyor.
# Double operand komutlar (2 operandlı; her biri 2 byte komut, immediate için ek kelime)
DOUBLE_OPTAB = {
    "MOV": 0x4,
    "ADD": 0x5,
    "SUB": 0x6,
    "CMP": 0x7,
    "AND": 0x8,
    "OR":  0x9,
    "XOR": 0xA,
    "DADD":0xB,
    "BIT": 0xC,
    "MUL": 0xD,
    "DIV": 0xE,
    "MOD": 0xF
}

# One operand komutlar (JMP, INC, DEC, CLR, NOT, NEG)
ONE_OPTAB = {
    "JMP": 0x1,   # JMP için jump kodlaması özel işlenecek
    "INC": 0x2,
    "DEC": 0x3,
    "CLR": 0x4,
    "NOT": 0x5,
    "NEG": 0x6
}

# Zero operand komutlar
ZERO_OPTAB = {
    "RET": 0x0
}

# MSP430 registerları (basitlik için; gerçek donanımda R0=PC, R1=SP vs. olabilir)
REGISTERS = {
    "R0": 0, "R1": 1, "R2": 2, "R3": 3,
    "R4": 4, "R5": 5, "R6": 6, "R7": 7,
    "R8": 8, "R9": 9, "R10": 10, "R11": 11,
    "R12": 12, "R13": 13, "R14": 14, "R15": 15
}


def first_pass(assembly_code):
    """
    Pass 1: Satırları okuyup etiketleri tespit edip sembol tablosunu oluşturur.
    Aynı zamanda START ve .DATA direktiflerini işleyerek ara listeye ekler.
    Her satırdan; adres, mnemonic ve operand listesini çıkarır.
    """
    lines = assembly_code.splitlines()
    locctr = 0
    intermediate = []  # Her giriş: (adres, mnemonic, operand_listesi)
    errors = []
    for line in lines:
        # Yorumları kaldır (';' den sonraki kısmı yok say)
        line = line.split(';')[0].strip()
        if not line:
            continue
        # Etiket varsa, ':' karakteriyle ayrılır
        if ':' in line:
            label, line = line.split(':', 1)
            label = label.strip()
            if label in SYMTAB:
                errors.append(f"Error: Duplicate label {label}")
            else:
                SYMTAB[label] = locctr
            line = line.strip()
            if not line:
                continue
        parts = line.split()
        mnemonic = parts[0].upper()
        operands = []
        if len(parts) > 1:
            # Virgülle ayrılmış operandlar
            operands = [op.strip() for op in ' '.join(parts[1:]).split(',')]
        # Direktif kontrolü:
        if mnemonic == "START":
            if operands:
                try:
                    # Başlangıç adresini ayarla
                    locctr = int(operands[0], 0)
                except ValueError:
                    errors.append(f"Error: Invalid START operand {operands[0]}")
            else:
                errors.append("Error: START directive requires an operand")
            # START direktifi ara listeye eklenmez.
            continue
        elif mnemonic == ".DATA":
            if not operands:
                errors.append(f"Error at {locctr:#04x}: .DATA requires an operand")
                continue
            # .DATA satırı için, operand olarak verilen değeri sakla
            intermediate.append((locctr, ".DATA", operands))
            locctr += 2  # veri için 2 byte alan ayrılıyor
            continue

        # Normal komut: ara listeye ekle
        intermediate.append((locctr, mnemonic, operands))
        locctr += 2  # Her komut 2 byte kabul ediliyor
    return intermediate, errors


def second_pass(intermediate):
    """
    Pass 2: Ara liste üzerinden makine kodu üretimi.
    - Double operand komutlar: İki operand bekler (dest register olmak zorunda).
    - One operand komutlar: JMP (özel jump offset hesaplaması) veya diğerleri basit register komutları.
    - Zero operand komut: RET.
    - .DATA direktifi: Sabit veri olarak 16-bit değer üretilir.
    """
    object_code = []
    errors = []
    for addr, mnemonic, operands in intermediate:
        # .DATA direktifi için
        if mnemonic == ".DATA":
            try:
                data_value = int(operands[0], 0)
            except ValueError:
                errors.append(f"Error at {addr:#04x}: Invalid data value {operands[0]}")
                continue
            object_code.append(f"{addr:#04x}: {data_value & 0xFFFF:#06x}")
            continue

        # Double operand komutlar
        if mnemonic in DOUBLE_OPTAB:
            if len(operands) != 2:
                errors.append(f"Error at {addr:#04x}: {mnemonic} requires 2 operands")
                continue
            dest, src = operands
            # Dest operand mutlaka register olmalı
            if dest not in REGISTERS:
                errors.append(f"Error at {addr:#04x}: Destination must be a register: {dest}")
                continue
            dest_reg = REGISTERS[dest]
            # Kaynak operandı çözümle:
            if src.startswith("#"):
                try:
                    immediate = int(src[1:], 0)
                except ValueError:
                    errors.append(f"Error at {addr:#04x}: Invalid immediate value {src}")
                    continue
                # Immediate için basit model: kaynak register alanı 0, addressing modu 3
                src_reg = 0
                mode = 3
                code = (DOUBLE_OPTAB[mnemonic] << 12) | (src_reg << 8) | (dest_reg << 4) | mode
                object_code.append(f"{addr:#04x}: {code:#06x}")
                extra_addr = addr + 2
                object_code.append(f"{extra_addr:#04x}: {immediate & 0xFFFF:#06x}")
            else:
                if src in REGISTERS:
                    src_reg = REGISTERS[src]
                    mode = 0  # register direct
                    code = (DOUBLE_OPTAB[mnemonic] << 12) | (src_reg << 8) | (dest_reg << 4) | mode
                    object_code.append(f"{addr:#04x}: {code:#06x}")
                elif src in SYMTAB:
                    immediate = SYMTAB[src]
                    mode = 4  # absolute addressing (basit model)
                    code = (DOUBLE_OPTAB[mnemonic] << 12) | (0 << 8) | (dest_reg << 4) | mode
                    object_code.append(f"{addr:#04x}: {code:#06x}")
                    extra_addr = addr + 2
                    object_code.append(f"{extra_addr:#04x}: {immediate & 0xFFFF:#06x}")
                else:
                    errors.append(f"Error at {addr:#04x}: Unknown source operand {src}")
                    continue

        # One operand komutlar (JMP, INC, DEC, CLR, NOT, NEG)
        elif mnemonic in ONE_OPTAB:
            if mnemonic == "JMP":
                if len(operands) != 1:
                    errors.append(f"Error at {addr:#04x}: JMP requires 1 operand")
                    continue
                target = operands[0]
                if target in SYMTAB:
                    target_addr = SYMTAB[target]
                else:
                    try:
                        target_addr = int(target, 0)
                    except ValueError:
                        errors.append(f"Error at {addr:#04x}: Invalid jump target {target}")
                        continue
                offset = (target_addr - (addr + 2)) // 2
                code = (ONE_OPTAB[mnemonic] << 12) | (offset & 0x0FFF)
                object_code.append(f"{addr:#04x}: {code:#06x}")
            else:
                # Diğer one operand komutlar: operand register olmalı
                if len(operands) != 1:
                    errors.append(f"Error at {addr:#04x}: {mnemonic} requires 1 operand")
                    continue
                op = operands[0]
                if op not in REGISTERS:
                    errors.append(f"Error at {addr:#04x}: Operand must be a register: {op}")
                    continue
                reg = REGISTERS[op]
                code = (ONE_OPTAB[mnemonic] << 12) | (reg << 8)
                object_code.append(f"{addr:#04x}: {code:#06x}")

        # Zero operand komutlar
        elif mnemonic in ZERO_OPTAB:
            if operands:
                errors.append(f"Error at {addr:#04x}: {mnemonic} takes no operands")
                continue
            code = (ZERO_OPTAB[mnemonic] << 12)
            object_code.append(f"{addr:#04x}: {code:#06x}")
        else:
            errors.append(f"Error at {addr:#04x}: Unknown mnemonic {mnemonic}")
    return object_code, errors


def assemble(assembly_code):
    intermediate, errors1 = first_pass(assembly_code)
    object_code, errors2 = second_pass(intermediate)
    errors = errors1 + errors2
    return object_code, errors

"""

if __name__ == "__main__":
    # Örnek kod: lab ödevine uygun, START ve .DATA direktiflerini de içeren basitleştirilmiş program
    sample_code = """ """
        START 0x4400
        LOOP: MOV R5, #0x3A
              ADD R5, COUNT
              SUB R5, #0x01
              CMP R5, #0x00
              INC R5
              DEC R5
              CLR R4
              NOT R4
              NEG R4
              MUL R5, R6
              DIV R5, R7
              MOD R5, COUNT
              JMP LOOP
        COUNT: .DATA 0x0005
              RET
    """"""
    obj, errs = assemble(sample_code)
    if errs:
        print("Derleme hataları:")
        for err in errs:
            print(err)
    else:
        print("Makine Kodu:")
        for line in obj:
            print(line)

"""