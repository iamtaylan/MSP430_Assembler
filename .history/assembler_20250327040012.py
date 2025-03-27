SYMTAB = {}  # Symbol Table

OPTAB = {
    # Format I Instructions (Two-operand instructions)
    "MOV": 0x4000,  "ADD": 0x5000,  "ADDC": 0x6000, "SUBC": 0x7000,
    "SUB": 0x8000,  "CMP": 0x9000,  "DADD": 0xA000, "BIT": 0xB000,
    "BIC": 0xC000,  "BIS": 0xD000,  "XOR": 0xE000,  "AND": 0xF000,

    # Format II Instructions
    "RRC": 0x1000,  "SWPB": 0x1080, "RRA": 0x1100,  "SXT": 0x1180,
    "PUSH": 0x1200, "CALL": 0x1280, "RET": 0x1300,

    # Format III Instructions
    "JNE": 0x2000,  "JEQ": 0x2400,  "JNC": 0x2800,  "JC": 0x2C00,
    "JN": 0x3000,   "JGE": 0x3400,  "JL": 0x3800,   "JMP": 0x3C00,

    # Pseudo-ops
    "START": None, "END": None, ".DATA": None, ".CODE": None, ".ORG": None
}

REGISTERS = {f"R{i}": i for i in range(16)}
REGISTERS["SP"] = 1  # Stack Pointer = R1

ADDRESSING_MODES = {
    "REGISTER": 0,      # Rn  --> As=00, ad=0
    "INDEXED": 1,       # X(Rn)  --> As=01, ad=1
    "SYMBOLIC": 1,      # ADDR   --> As=01, ad=1
    "ABSOLUTE": 1,      # &ADDR  --> As=01, ad=1
    "INDIRECT": 2,      # @Rn    --> As=10
    "INDIRECT_INC": 3,  # @Rn+   --> As=11
    "IMMEDIATE": 3      # #N     --> As=11
}

LOCCTR = 0
starting_address = 0
program_length = 0
intermediate_file = []
object_code = []
errors = []

def log_error(message):
    errors.append(message)

def parse_operand(operand):
    if operand and "," in operand:
        src, dst = map(str.strip, operand.split(",", 1))
        return src, dst
    return operand, None

def get_addressing_mode(operand):
    if not operand:
        return None, None
        
    if operand.startswith("#"):
        return "IMMEDIATE", operand[1:]
    elif operand.startswith("&"):
        return "ABSOLUTE", operand[1:]
    elif operand.startswith("@"):
        if operand.endswith("+"):
            return "INDIRECT_INC", operand[1:-1]
        return "INDIRECT", operand[1:]
    elif operand in REGISTERS:
        return "REGISTER", operand
    elif "(" in operand and ")" in operand:
        return "INDEXED", operand
    else:
        return "SYMBOLIC", operand

def pass1(assembly_code):
    global LOCCTR, starting_address, program_length
    lines = assembly_code.splitlines()
    
    for line in lines:
        line = line.split(";")[0].strip()
        if not line:
            continue

        parts = line.split()
        if not parts:
            continue

        label = parts[0].strip(":") if parts[0].endswith(":") else None
        opcode = parts[1] if label and len(parts) > 1 else parts[0]
        operand = " ".join(parts[2:]) if label and len(parts) > 2 else (
                 " ".join(parts[1:]) if not label and len(parts) > 1 else None)

        if label:
            if label in SYMTAB:
                log_error(f"Duplicate symbol: '{label}'")
                continue
            SYMTAB[label] = LOCCTR

        if opcode == "START":
            starting_address = int(operand, 16) if operand else 0
            LOCCTR = starting_address
            continue
        if opcode == "END":
            program_length = LOCCTR - starting_address
            break

        if opcode in OPTAB:
            if opcode in ["MOV", "ADD", "SUB", "CMP", "AND", "XOR", "BIC", "BIS", "BIT", "DADD"]:
                src, dst = parse_operand(operand)
                src_mode, _ = get_addressing_mode(src) if src else (None, None)
                dst_mode, _ = get_addressing_mode(dst) if dst else (None, None)
                
                extra = 0
                if src_mode in ["IMMEDIATE", "ABSOLUTE"]:
                    extra += 2
                if dst_mode in ["IMMEDIATE", "ABSOLUTE"]:
                    extra += 2
                LOCCTR += 2 + extra  # 1 word for instruction + extra words for operands

            else:
                LOCCTR += 2  # Format II/III instructions
        elif opcode:
            log_error(f"Unknown instruction: '{opcode}'")

        intermediate_file.append((label, opcode, operand, LOCCTR))

def pass2():
    global object_code
    for label, opcode, operand, loc in intermediate_file:
        if opcode in ["START", "END"]:
            continue

        instruction = OPTAB.get(opcode)
        if not instruction:
            continue

        if opcode in ["MOV", "ADD", "SUB", "CMP", "AND", "XOR", "BIC", "BIS", "BIT", "DADD"]:
            src, dst = parse_operand(operand)
            src_mode, src_val = get_addressing_mode(src)
            dst_mode, dst_val = get_addressing_mode(dst)

            # Handle source operand
            if src_val in REGISTERS:
                src_reg = REGISTERS[src_val]
            elif src_val in SYMTAB:
                src_reg = SYMTAB[src_val]
            else:
                log_error(f"Undefined symbol in source operand: '{src_val}'")
                src_reg = 0
            if src_mode == "INDIRECT_INC":
                src_reg |= 0x10  # Set auto-increment bit

            # Handle destination operand
            if dst_val in REGISTERS:
                dst_reg = REGISTERS[dst_val]
            elif dst_val in SYMTAB:
                dst_reg = SYMTAB[dst_val]
            else:
                log_error(f"Undefined symbol in destination operand: '{dst_val}'")
                dst_reg = 0
            if dst_mode == "INDIRECT_INC":
                dst_reg |= 0x10  # Set auto-increment bit


            # Build instruction word according to MSP430 format:
            # opcode (4 bits), S-Reg (4 bits), Ad (1 bit), B/W (1 bit), As (2 bits), D-Reg (4 bits)
            opcode_field = (instruction >> 12) & 0xF   # Extract 4-bit opcode from OPTAB value
            s_reg = src_reg                            # Source register becomes S-Reg
            ad = 0 if dst_mode == "REGISTER" else 1      # Destination addressing: 0 for REGISTER, 1 otherwise
            b_w = 0                                    # Default B/W = 0 (word operation)
            as_field = ADDRESSING_MODES[src_mode]       # Source addressing mode (As), already in 2-bit range per new mapping
            d_reg = dst_reg                            # Destination register becomes D-Reg

            instruction_word = (
                (opcode_field << 12) |
                ((s_reg & 0xF) << 8) |
                ((ad & 0x1) << 7) |
                ((b_w & 0x1) << 6) |
                ((as_field & 0x3) << 4) |
                (d_reg & 0xF)
            )
            object_code.append((loc, instruction_word))

            # Handle additional words for immediate/absolute
            if src_mode in ["IMMEDIATE", "ABSOLUTE"]:
                object_code.append((loc + 2, int(src_val, 16)))
            if dst_mode in ["IMMEDIATE", "ABSOLUTE"]:
                object_code.append((loc + 2, int(dst_val, 16)))

        elif opcode in ["RRC", "SWPB", "RRA", "SXT", "PUSH", "CALL"]:
            object_code.append((loc, instruction))

        elif opcode in ["JMP", "JNE", "JEQ", "JNC", "JC", "JN", "JGE", "JL"]:
            target_addr = SYMTAB.get(operand, 0)
            offset = (target_addr - (loc + 2)) // 2
            instruction_word = instruction | (offset & 0x3FF)
            object_code.append((loc, instruction_word))

def save_object_code(filename="output.hex"):
    with open(filename, "w") as f:
        for loc, code in object_code:
            f.write(f"{hex(loc)}: {hex(code)}\n")
    print(f"Machine code saved to {filename}")

def main():
    print("Enter assembly code (type 'END' to finish):")
    assembly_code = ""
    while True:
        line = input()
        assembly_code += line + "\n"
        if line.strip() == "END":
            break

    pass1(assembly_code)
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(error)
        return

    pass2()
    save_object_code()
    
    print("\nGenerated Object Code:")
    for loc, code in object_code:
        print(f"{hex(loc)}: {hex(code)} ({bin(code)[2:].zfill(16)})")

if __name__ == "__main__":
    main()