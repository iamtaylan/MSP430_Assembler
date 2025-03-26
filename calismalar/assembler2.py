# assembler.py

SYMTAB = {}
# Gerçek opcode değerlerini tutuyoruz (MSP430 double operand komutları için):
OPTAB_DOUBLE = {
    "MOV": 4, "ADD": 5, "SUB": 6, "CMP": 7, "AND": 8, "OR": 9, "XOR": 0xA, "DADD": 0xB, "BIT": 0xC
}
# Tek operandlı, MSP430’un bir operandlı komutları (örneğin PUSH, POP, SWPB, RRA, SXT)
OPTAB_ONE = {
    "PUSH": 0x1, "POP": 0x2, "SWPB": 0x3, "RRA": 0x4, "SXT": 0x5
}
# Sıfır operandlı komutlar
OPTAB_ZERO = {
    "RET": 0x0
}
# Atlama komutları için jump formatında; burada koşul kodlarını MSP430 jump formatındaki mantığa benzetiyoruz.
JUMP_CONDITIONS = {
    "JMP": 0, "JZ": 1, "JNZ": 2, "CALL": 3
}

# MSP430’ta registerlar (R0: PC, R1: SP, R2: SR, R3: CG) şeklinde tanımlanır.
REGISTERS = {f"R{i}": i for i in range(16)}
# MSP430’da özel register’lar
REGISTERS["PC"] = 0  # Program Counter (R0)
REGISTERS["SP"] = 1  # Stack Pointer (R1)
REGISTERS["SR"] = 2  # Status Register (R2)
REGISTERS["CG"] = 3  # Constant Generator (R3)

# MSP430 addressing modları için; 
# Double operand talimatlarda:
#   - Kaynak için:
#       00: Register direct
#       01: Indexed (örneğin: label için, PC’ye göre)
#       11: Immediate (MSP430’ta immediate, R3 ve As=11 ile kodlanır)
#   - Hedef için: 
#       0: Register direct (tek bit)
#
# Tek operandlı komutlarda da benzer mantık kullanılacaktır.
# (Burada, Ad değeri sadece 0 (register direct) veya 1 (indexed/PC-relative) olarak alınacaktır)
ADDRESSING_MODES = {
    "REGISTER": 0,      # register direct
    "INDEXED": 1,       # örn: label ya da bellek adresi (PC-relative)
    "IMMEDIATE": 3      # immediate modu, MSP430 için As=11
}


def assemble(assembly_code):
    errors = []
    object_code = []
    SYMTAB.clear()
    LOCCTR = 0 
    intermediate_file = []  
    
    # 1. Geçiş: Sembol tablosu oluşturma ve ara dosya hazırlama
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
        
        # Direktifler
        if opcode == "START":
            try:
                LOCCTR = int(operand_str, 16) if operand_str else 0
            except ValueError:
                errors.append("Hata: START operandı geçerli bir hexadecimal sayı olmalı")
            continue
        if opcode == "END":
            SYMTAB["END"] = LOCCTR
            break
        
        # Her talimat en az 1 kelime kaplar, fakat bazı addressing modları ek kelime gerektirebilir.
        current_address = LOCCTR
        # İlk kelime için 2 byte artış (ek kelime varsa daha sonra eklenir)
        LOCCTR += 2
        
        operands = []
        if operand_str:
            # Virgülle ayrılmış operandlar
            operands = [op.strip() for op in operand_str.split(",") if op.strip()]
        
        intermediate_file.append((opcode, operands, current_address))
    
    # 2. Geçiş: Makine kodu üretimi
    for opcode, operands, addr in intermediate_file:
        # Öncelikle double operand komutlarını kontrol edelim
        if opcode in OPTAB_DOUBLE:
            if len(operands) != 2:
                errors.append(f"Hata: {opcode} komutu iki operand gerektirir")
                continue
            # Hedef operand: MSP430 double operandlarda hedef sadece register direct modunda olabilir.
            dest = operands[0]
            if dest not in REGISTERS:
                errors.append(f"Hata: {opcode} komutunda hedef operand '{dest}' geçerli bir register olmalı")
                continue
            dest_reg = REGISTERS[dest]
            # Kaynak operand
            src = operands[1]
            extra_words = []
            # Eğer immediate ise:
            if src.startswith("#"):
                # Immediate mod için MSP430’da R3 kullanılır ve addressing modu 11 (yani 3) olarak set edilir.
                try:
                    imm_value = int(src[1:], 16)
                except ValueError:
                    errors.append(f"Hata: Geçersiz immediate değer '{src}'")
                    continue
                src_reg = REGISTERS["CG"]  # Constant Generator (R3)
                As = ADDRESSING_MODES["IMMEDIATE"]
                # Ek kelime olarak immediate değeri eklenir.
                extra_words.append(imm_value & 0xFFFF)
            elif src in REGISTERS:
                src_reg = REGISTERS[src]
                As = ADDRESSING_MODES["REGISTER"]
            elif src in SYMTAB:
                # Eğer sembol ise, PC relative (indexed) adresleme kullanıyoruz.
                src_reg = REGISTERS["PC"]
                As = ADDRESSING_MODES["INDEXED"]
                extra_words.append(SYMTAB[src] & 0xFFFF)
            else:
                errors.append(f"Hata: {opcode} komutunda kaynak operand '{src}' tanınamadı")
                continue
            # Hedef operand için addressing modu sabit: register direct (Ad = 0)
            Ad = 0
            opcode_val = OPTAB_DOUBLE[opcode]
            # Double operand talimatın kodlaması:
            # [15:12] opcode, [11:8] src_reg, [7:4] dest_reg, [3:2] As, [1:0] Ad
            instr_word = (opcode_val << 12) | (src_reg << 8) | (dest_reg << 4) | ((As << 2) | Ad)
            object_code.append(f"{hex(addr)}: {hex(instr_word)}")
            # Eğer ekstra kelime varsa, bunları da çıktı olarak ekleyelim (adres artışını takip etmek için)
            extra_addr = addr + 2
            for word in extra_words:
                object_code.append(f"{hex(extra_addr)}: {hex(word)}")
                extra_addr += 2
                LOCCTR += 2  # ekstra kelime adres artışı
            continue
        
        # Tek operandlı komutlar (jump olmayan) kontrolü:
        if opcode in OPTAB_ONE:
            if len(operands) != 1:
                errors.append(f"Hata: {opcode} komutu bir operand gerektirir")
                continue
            op = operands[0]
            extra_words = []
            if op.startswith("#"):
                try:
                    imm_value = int(op[1:], 16)
                except ValueError:
                    errors.append(f"Hata: Geçersiz immediate değer '{op}'")
                    continue
                op_reg = REGISTERS["CG"]  # R3
                addr_mode = ADDRESSING_MODES["IMMEDIATE"]
                extra_words.append(imm_value & 0xFFFF)
            elif op in REGISTERS:
                op_reg = REGISTERS[op]
                addr_mode = ADDRESSING_MODES["REGISTER"]
            elif op in SYMTAB:
                op_reg = REGISTERS["PC"]
                addr_mode = ADDRESSING_MODES["INDEXED"]
                extra_words.append(SYMTAB[op] & 0xFFFF)
            else:
                errors.append(f"Hata: {opcode} komutunda operand '{op}' tanınamadı")
                continue
            opcode_val = OPTAB_ONE[opcode]
            # Tek operandlı komut için basit format: [15:12] opcode, [11:8] op_reg, [7:4] addr_mode, [3:0] sıfır
            instr_word = (opcode_val << 12) | (op_reg << 8) | (addr_mode << 4)
            object_code.append(f"{hex(addr)}: {hex(instr_word)}")
            extra_addr = addr + 2
            for word in extra_words:
                object_code.append(f"{hex(extra_addr)}: {hex(word)}")
                extra_addr += 2
                LOCCTR += 2
            continue
        
        # Atlama (jump) komutları: JMP, JZ, JNZ, CALL
        if opcode in JUMP_CONDITIONS:
            if len(operands) != 1:
                errors.append(f"Hata: {opcode} komutu bir operand (hedef adres) gerektirir")
                continue
            target = operands[0]
            # Hedef adres bir sembol ise, sembol tablosundan alalım
            if target in SYMTAB:
                target_addr = SYMTAB[target]
            else:
                try:
                    target_addr = int(target, 16)
                except ValueError:
                    errors.append(f"Hata: {opcode} komutu için geçersiz hedef '{target}'")
                    continue
            # MSP430 jump komutları, 10-bit imzalı offset içerir.
            # Offset, hedef adres ile (mevcut jump komutunun adres + 2) farkı (word cinsinden) şeklinde hesaplanır.
            offset = (target_addr - (addr + 2)) // 2
            # 10-bit imzalı sayı aralığı kontrolü (-512 ile 511)
            if offset < -512 or offset > 511:
                errors.append(f"Hata: {opcode} komutu için offset {offset} 10-bit aralıkta değil")
                continue
            cond = JUMP_CONDITIONS[opcode]
            # Jump formatı: [15:13]=0b001, [12:10]=koşul kodu (3 bit olarak burada örnekleniyor), [9:0]=offset (10 bit)
            instr_word = (0b001 << 13) | ((cond & 0x7) << 10) | (offset & 0x3FF)
            object_code.append(f"{hex(addr)}: {hex(instr_word)}")
            continue
        
        # Sıfır operandlı komutlar (örneğin RET)
        if opcode in OPTAB_ZERO:
            if len(operands) != 0:
                errors.append(f"Hata: {opcode} komutu operand almaz")
                continue
            opcode_val = OPTAB_ZERO[opcode]
            # Örneğin RET için basitçe sadece opcode alanı kullanılır.
            instr_word = (opcode_val << 12)
            object_code.append(f"{hex(addr)}: {hex(instr_word)}")
            continue
        
        errors.append(f"Hata: Desteklenmeyen komut '{opcode}'")
    
    return object_code, errors


# Örnek kullanım:
if __name__ == "__main__":
    sample_code = """
        START 0x4400
        LOOP: MOV R5, #0x3A
              ADD R5, COUNT
              JZ ENDLOOP
              JMP LOOP
        COUNT: .DATA 0x0005
        ENDLOOP: RET
        END
    """
    obj_code, errs = assemble(sample_code)
    if errs:
        print("Derleme hataları:")
        for e in errs:
            print(e)
    else:
        print("Makine kodu:")
        for line in obj_code:
            print(line)
