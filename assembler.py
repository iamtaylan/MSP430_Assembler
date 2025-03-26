SYMTAB = {}
OPTAB = {
    "MOV":  0x4000,
    "ADD":  0x5000,
    "SUB":  0x8000,
    "CMP":  0x9000,
    "JMP":  0x3C00,  # Koşulsuz atlama
    "JZ":   0x2400,  # Sıfır ise atla
    "JNZ":  0x2000,  # Sıfır değilse atla
    "CALL": 0x3D00,
    "RET":  0x3E00,
    "PUSH": None,   # MSP430’da PUSH/POP pseudo komuttur
    "POP":  None,
    #"AND":  None,
    #"OR":   None,
    #"XOR":  None,
    "BIT":  0xB000,
    "SWPB": 0x1180,
    "DADD": 0xA000,
    "RRA":  0x1280,
    "SXT":  0x1300,
    "START": None,
    "END": None,
    ".DATA": None,
    ".CODE": None,
    ".ORG": None
}

REGISTERS = {f"R{i}": i for i in range(16)}
REGISTERS["SP"] = 1  # Stack Pointer (R1)

ADDRESSING_MODES = {
    "REGISTER": 0x0,
    "IMMEDIATE": 0x3,
    "ABSOLUTE": 0x4
}

TWO_OPERAND_OPS = {"MOV", "ADD", "SUB", "CMP", "AND", "OR", "XOR", "DADD", "BIT"}
ONE_OPERAND_OPS = {"JMP", "JZ", "JNZ", "CALL", "PUSH", "POP", "SWPB", "RRA", "SXT"}
ZERO_OPERAND_OPS = {"RET"}

def assemble(assembly_code):
    errors = []
    object_code = []
    SYMTAB.clear()
    LOCCTR = 0 
    intermediate_file = []  
    
    # 1. Geçiş: Sembol tablosu oluşturma
    for line in assembly_code.splitlines():
        line = line.split(";")[0].strip()
        if not line:
            continue
        
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
        
        parts = line.split(None, 1)
        opcode = parts[0].strip().upper()
        operand_str = parts[1].strip() if len(parts) > 1 else ""
        
        if opcode == "START":
            try:
                LOCCTR = int(operand_str, 16) if operand_str else 0
            except ValueError:
                errors.append("Hata: START operandı geçerli bir hexadecimal sayı olmalı")
            continue
        if opcode == "END":
            SYMTAB["END"] = LOCCTR
            break
        
        current_address = LOCCTR
        LOCCTR += 2
        
        operands = []
        if operand_str:
            operands = [op.strip() for op in operand_str.split(",") if op.strip()]
        
        intermediate_file.append((opcode, operands, current_address))
    
    # 2. Geçiş: Makine kodu üretimi
    for opcode, operands, addr in intermediate_file:
        if opcode not in OPTAB or OPTAB[opcode] is None:
            errors.append(f"Hata at {hex(addr)}: Bilinmeyen veya desteklenmeyen komut '{opcode}'")
            continue
        
        opcode_val = OPTAB[opcode]
        opcode_nibble = opcode_val >> 12
        machine_code = 0
        
        if opcode in TWO_OPERAND_OPS:
            if len(operands) != 2:
                errors.append(f"Hata at {hex(addr)}: {opcode} komutu iki operand gerektirir")
                continue
            # MSP430 için beklenen sıra: src, dest.
            src = operands[0]
            dest = operands[1]
            if dest.startswith("#") and src in REGISTERS:
                src, dest = dest, src

            if dest not in REGISTERS:
                errors.append(f"Hata at {hex(addr)}: Destination must be a register: {dest}")
                continue
            dest_reg = REGISTERS[dest]
            
            if src.startswith("#"):
                try:
                    src_value = int(src[1:], 16)
                except ValueError:
                    errors.append(f"Hata at {hex(addr)}: Geçersiz immediate değer '{src}'")
                    continue
                src_mode = ADDRESSING_MODES["IMMEDIATE"]
            elif src in REGISTERS:
                src_value = REGISTERS[src]
                src_mode = ADDRESSING_MODES["REGISTER"]
            elif src in SYMTAB:
                src_value = SYMTAB[src]
                src_mode = ADDRESSING_MODES["ABSOLUTE"]
            else:
                errors.append(f"Hata at {hex(addr)}: Bilinmeyen operand '{src}'")
                continue
            
            # Örneğin: MOV: makine kodu = [opcode(4)][src (4)][dest (4)]
            machine_code = (opcode_nibble << 12) | ((src_value & 0xF) << 4) | (dest_reg & 0xF)
        
        elif opcode in ONE_OPERAND_OPS:
            if len(operands) != 1:
                errors.append(f"Hata at {hex(addr)}: {opcode} komutu bir operand gerektirir")
                continue
            op = operands[0]
            if op.startswith("#"):
                errors.append(f"Hata at {hex(addr)}: {opcode} komutunda immediate operand kullanılmaz")
                continue
            elif op in REGISTERS:
                op_value = REGISTERS[op]
            elif op in SYMTAB:
                op_value = SYMTAB[op]
            else:
                errors.append(f"Hata at {hex(addr)}: Bilinmeyen operand '{op}'")
                continue
            
            machine_code = opcode_val | (op_value & 0xFF)
        
        elif opcode in ZERO_OPERAND_OPS:
            if len(operands) != 0:
                errors.append(f"Hata at {hex(addr)}: {opcode} komutu operand almaz")
                continue
            machine_code = opcode_val
        
        else:
            errors.append(f"Hata at {hex(addr)}: Desteklenmeyen komut '{opcode}'")
            continue
        
        # İstenen çıktı formatı: ADDR, HEX, BIN
        object_code.append(f"ADDR: {hex(addr)} | HEX: {hex(machine_code)} | BIN: {machine_code:016b}")
    
    # Final çıktıyı "Object Code:" başlığı ile döndürmek için:
    object_code.insert(0, "Object Code:")
    return object_code, errors
