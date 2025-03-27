START 0x1000

; Format I (İki-operand) işlemleri:
MOV   R2, R3                ; REGISTER -> REGISTER adresleme
ADD   #0x1234, R4           ; Immediate adresleme (kaynak operand başında #)
SUB   &0x5678, R5           ; Absolute adresleme (kaynak operand başında &)
CMP   @R6, R7               ; Indirect adresleme (kaynak operand başında @)
DADD  R8, R9                ; REGISTER -> REGISTER
XOR   0x20(R10), R11        ; Indexed adresleme (operand içinde parantez)
BIS   DATA1, R12            ; Symbolic adresleme (etiket kullanımı)
AND   @R13+, R14            ; Indirect Increment adresleme (operand sonunda +)

; Format II işlemleri:
RRC   R15                  ; Tek kelime, Format II
SWPB  R0
RRA   R1
SXT   R2
PUSH  R3
CALL  SUBRTN               ; Alt programa çağrı

; Format III (Branch) işlemleri:
JNE   LAB2
JEQ   LAB3
JNC   LAB4
JC    LAB5
JN    LAB6
JGE   LAB7
JL    LAB8
JMP   LAB9

; Branch hedefleri ve veri tanımlamaları:
DATA1: .DATA 0x55         ; Symbolic adresleme için kullanılan etiket
LAB2: MOV  R2, R3         ; JNE için hedef
LAB3: ADD  R4, R5         ; JEQ için hedef
LAB4: SUB  R6, R7         ; JNC için hedef
LAB5: CMP  R8, R9         ; JC için hedef
LAB6: DADD R10, R11       ; JN için hedef
LAB7: BIT  R12, R13       ; JGE için hedef
LAB8: BIC  R14, R15       ; JL için hedef
LAB9: BIS  R0, R1         ; JMP için hedef

SUBRTN: RET               ; Alt programın dönüş komutu

.ORG  0x2000              ; Yeni bir bellek alanı başlat
.CODE                    ; Kod bölümü tanımlaması

END
