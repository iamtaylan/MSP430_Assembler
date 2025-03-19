# assembler.py

SYMTAB = {}
OPTAB = {
    "MOV": 0x1000, "ADD": 0x2000, "SUB": 0x3000, "CMP": 0x4000, "JMP": 0x5000,
    "JZ": 0x6000, "JNZ": 0x7000, "CALL": 0x8000, "RET": 0x9000, "PUSH": 0xA000, "POP": 0xB000,
    "AND": 0xC000, "OR": 0xD000, "XOR": 0xE000, "BIT": 0xF000, "SWPB": 0xD100, "DADD": 0xD200,
    "RRA": 0xD300, "SXT": 0xD400, "START": None, "END": None, ".DATA": None, ".CODE": None, ".ORG": None
}

REGISTERS = {f"R{i}": i for i in range(16)}
REGISTERS["SP"] = 1  # Stack Pointer (R1 olarak tanımlı)

ADDRESSING_MODES = {
    "REGISTER": 0x0,
    "IMMEDIATE": 0x3,
    "ABSOLUTE": 0x4
}

# Talimat türlerini belirleyelim
TWO_OPERAND_OPS = {"MOV", "ADD", "SUB", "CMP", "AND", "OR", "XOR", "BIT"}
ONE_OPERAND_OPS = {"JMP", "JZ", "JNZ", "CALL", "PUSH", "POP", "SWPB", "DADD", "RRA", "SXT"}
ZERO_OPERAND_OPS = {"RET"}

def assemble(assembly_code):
    errors = []
    object_code = []
    SYMTAB.clear()
    LOCCTR = 0
    intermediate_file = []
    
    # Birinci geçiş: Sembol tablosu oluşturma ve ara dosya hazırlama
    for line in assembly_code.splitlines():
        # Yorumları kaldır ve boşlukları temizle
        line = line.split(";")[0].strip()
        if not line:
            continue
        
        # Eğer satırda label varsa (':' karakteri ile)
        if ":" in line:
            label_part, line = line.split(":", 1)
            label = label_part.strip()
            if label in SYMTAB:
                errors.append(f"Hata: '{label}' etiketi tekrarlandı")
            else:
                SYMTAB[label] = LOCCTR
            line = line.strip()
            if not line:
                continue
        
        # Opcode ve operand kısmını ayıralım
        parts = line.split(None, 1)
        opcode = parts[0].strip()
        operand_str = parts[1].strip() if len(parts) > 1 else ""
        
        # Direktif kontrolü
        if opcode == "START":
            try:
                LOCCTR = int(operand_str, 16) if operand_str else 0
            except ValueError:
                errors.append("Hata: START operandı geçerli bir hexadecimal sayı olmalı")
            continue
        if opcode == "END":
            # END direktifi için SYMTAB'e END etiketini ekleyip derlemeyi sonlandırıyoruz.
            SYMTAB["END"] = LOCCTR
            break
        
        # Mevcut adresi kaydet ve her talimat için 2 byte artış yapalım
        current_address = LOCCTR
        LOCCTR += 2
        
        # Operandlar varsa, virgülle ayırıp listeye aktaralım
        operands = []
        if operand_str:
            operands = [op.strip() for op in operand_str.split(",") if op.strip()]
        
        intermediate_file.append((opcode, operands, current_address))
    
    # İkinci geçiş: Makine kodu üretimi
    for opcode, operands, addr in intermediate_file:
        if opcode not in OPTAB or OPTAB[opcode] is None:
            errors.append(f"Hata: Bilinmeyen komut '{opcode}'")
            continue
        
        # OPTAB'daki değerin en yüksek 4 bitini opcode nibble olarak alıyoruz.
        opcode_val = OPTAB[opcode]
        opcode_nibble = opcode_val >> 12
        
        machine_code = 0
        
        if opcode in TWO_OPERAND_OPS:
            if len(operands) != 2:
                errors.append(f"Hata: {opcode} komutu iki operand gerektirir")
                continue
            dest = operands[0]
            src = operands[1]
            # Hedef operand register olmalıdır
            if dest not in REGISTERS:
                errors.append(f"Hata: Bilinmeyen operand '{dest}' (destinasyon register olmalı)")
                continue
            dest_reg = REGISTERS[dest]
            
            # Kaynak operand için addressing mode belirle
            if src.startswith("#"):
                try:
                    src_value = int(src[1:], 16)
                except ValueError:
                    errors.append(f"Hata: Geçersiz immediate değer '{src}'")
                    continue
                src_mode = ADDRESSING_MODES["IMMEDIATE"]
            elif src in REGISTERS:
                src_value = REGISTERS[src]
                src_mode = ADDRESSING_MODES["REGISTER"]
            elif src in SYMTAB:
                src_value = SYMTAB[src]
                src_mode = ADDRESSING_MODES["ABSOLUTE"]
            else:
                errors.append(f"Hata: Bilinmeyen operand '{src}'")
                continue
            
            # 16-bit makine kodu: [opcode(4)][dest register(4)][src_mode(4)][src_value'in düşük 4 biti]
            machine_code = (opcode_nibble << 12) | (dest_reg << 8) | (src_mode << 4) | (src_value & 0xF)
        
        elif opcode in ONE_OPERAND_OPS:
            if len(operands) != 1:
                errors.append(f"Hata: {opcode} komutu bir operand gerektirir")
                continue
            op = operands[0]
            if op.startswith("#"):
                try:
                    op_value = int(op[1:], 16)
                except ValueError:
                    errors.append(f"Hata: Geçersiz immediate değer '{op}'")
                    continue
                op_mode = ADDRESSING_MODES["IMMEDIATE"]
            elif op in REGISTERS:
                op_value = REGISTERS[op]
                op_mode = ADDRESSING_MODES["REGISTER"]
            elif op in SYMTAB:
                op_value = SYMTAB[op]
                op_mode = ADDRESSING_MODES["ABSOLUTE"]
            else:
                errors.append(f"Hata: Bilinmeyen operand '{op}'")
                continue
            
            # 16-bit makine kodu: [opcode(4)][operand mode(4)][operand değerin düşük 8 biti]
            machine_code = (opcode_nibble << 12) | (op_mode << 8) | (op_value & 0xFF)
        
        elif opcode in ZERO_OPERAND_OPS:
            if len(operands) != 0:
                errors.append(f"Hata: {opcode} komutu operand almaz")
                continue
            machine_code = (opcode_nibble << 12)
        
        else:
            errors.append(f"Hata: Desteklenmeyen komut '{opcode}'")
            continue
        
        object_code.append(f"{hex(addr)}: {hex(machine_code)}")
    
    return object_code, errors

