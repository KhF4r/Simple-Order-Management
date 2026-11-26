"""Pemeriksa tipe numerik untuk DSL NumType (parser: Lark / LALR).

Alur:   teks DSL --Lark--> parse tree --Interpreter (aturan tipe)--> daftar galat

Aturan tipe:
  literal     : "42" -> int, "3.14" -> float, "..." -> str
  + - *       : int⊕int -> int | int⊕float, float⊕float -> float (pelebaran int->float)
  /           : selalu float (true division, seperti Python)
  str + str   : str.   Operasi lain yang melibatkan str -> GALAT
  deklarasi   : tipe nilai harus bisa ditampung tipe variabel
                  int  -> float  boleh (pelebaran)      float -> int  GALAT (penyempitan)
                  str <-> angka  GALAT
  assign      : variabel harus sudah dideklarasikan; tipenya tetap (statis)
  panggilan   : fungsi harus dideklarasikan, jumlah & tipe argumen harus cocok
"""
import os, sys
from lark import Lark
from lark.exceptions import UnexpectedInput
from lark.visitors import Interpreter

DIR = os.path.dirname(os.path.abspath(__file__))
PARSER = Lark(open(os.path.join(DIR, "numtype.lark")).read(), parser="lalr", propagate_positions=True)
ERR = "?"          # tipe "tidak diketahui" setelah galat; mencegah galat beruntun
NUM = {"int", "float"}


class TypeChecker(Interpreter):
    def __init__(self):
        self.vars, self.fns, self.errors, self.log = {}, {}, [], []

    # ---- util
    def line(self, t): return getattr(t.meta, "line", 0)
    def err(self, t, kode, pesan): self.errors.append((self.line(t), kode, pesan))
    def trace(self, t, teks): self.log.append((self.line(t), teks))

    @staticmethod
    def assignable(nilai, target):
        return nilai == target or (nilai == "int" and target == "float")

    def cek_tampung(self, t, nilai, target, konteks):
        if nilai == ERR or target == ERR: return
        if self.assignable(nilai, target):
            if nilai != target:
                self.trace(t, f"{konteks}: {nilai} → {target}  (pelebaran implisit, boleh)")
            return
        if nilai == "float" and target == "int":
            self.err(t, "E-NARROW", f"{konteks}: float tidak bisa disimpan ke int (penyempitan, presisi hilang)")
        else:
            self.err(t, "E-MISMATCH", f"{konteks}: tipe {nilai} tidak cocok dengan {target}")

    # ---- program & pernyataan
    def start(self, t):
        for s in t.children: self.visit(s)

    def type(self, t): return {"int": "int", "float": "float", "str": "str"}[str(t.children[0])]

    def decl(self, t):
        tipe, nama, ekspr = self.visit(t.children[0]), str(t.children[1]), t.children[2]
        nilai = self.visit(ekspr)
        if nama in self.vars:
            self.err(t, "E-REDECL", f"variabel '{nama}' sudah dideklarasikan sebagai {self.vars[nama]}")
        self.cek_tampung(t, nilai, tipe, f"deklarasi {tipe} {nama}")
        self.vars.setdefault(nama, tipe)
        self.trace(t, f"decl   {tipe} {nama} = <{nilai}>")

    def assign(self, t):
        nama, nilai = str(t.children[0]), self.visit(t.children[1])
        if nama not in self.vars:
            self.err(t, "E-UNDECL", f"variabel '{nama}' belum dideklarasikan (tidak ada di scope)")
            return
        self.cek_tampung(t, nilai, self.vars[nama], f"assignment ke {nama} ({self.vars[nama]})")
        self.trace(t, f"assign {nama}({self.vars[nama]}) = <{nilai}>")

    def fndecl(self, t):
        nama = str(t.children[0])
        ps = [(self.visit(p.children[0]), str(p.children[1])) for p in (t.children[1].children if t.children[1] else [])]
        self.fns[nama] = ([p[0] for p in ps], self.visit(t.children[2]))
        self.trace(t, f"fn     {nama}({', '.join(a+' '+b for a, b in ps)}) -> {self.fns[nama][1]}")

    # ---- ekspresi (mengembalikan tipe)
    def num(self, t): return "float" if "." in str(t.children[0]) else "int"
    def string(self, t): return "str"

    def var(self, t):
        nama = str(t.children[0])
        if nama not in self.vars:
            self.err(t, "E-UNDECL", f"variabel '{nama}' belum dideklarasikan (tidak ada di scope)")
            return ERR
        return self.vars[nama]

    def neg(self, t):
        x = self.visit(t.children[0])
        if x == ERR: return ERR
        if x not in NUM:
            self.err(t, "E-OP", f"operator '-' unary tidak berlaku untuk {x}"); return ERR
        return x

    def binop(self, t):
        a, op, b = self.visit(t.children[0]), str(t.children[1]), self.visit(t.children[2])
        if ERR in (a, b): return ERR
        if a in NUM and b in NUM:
            hasil = "float" if (op == "/" or "float" in (a, b)) else "int"
        elif a == b == "str" and op == "+":
            hasil = "str"
        else:
            self.err(t, "E-OP", f"operator '{op}' tidak didefinisikan untuk {a} dan {b}"); return ERR
        self.trace(t, f"binop  {a} {op} {b} → {hasil}")
        return hasil

    def call(self, t):
        nama = str(t.children[0])
        args = t.children[1].children if t.children[1] else []
        tipe_arg = [self.visit(a) for a in args]
        if nama not in self.fns:
            self.err(t, "E-UNDEF-FN", f"fungsi '{nama}' belum dideklarasikan"); return ERR
        param, ret = self.fns[nama]
        if len(param) != len(tipe_arg):
            self.err(t, "E-ARITY", f"{nama}() butuh {len(param)} argumen, diberi {len(tipe_arg)}"); return ret
        for i, (p, a) in enumerate(zip(param, tipe_arg), 1):
            self.cek_tampung(t, a, p, f"argumen ke-{i} untuk {nama}()")
        return ret


def periksa(teks):
    """-> (tree, TypeChecker) ; raise UnexpectedInput bila sintaks salah."""
    tree = PARSER.parse(teks)
    tc = TypeChecker(); tc.visit(tree)
    return tree, tc


if __name__ == "__main__":
    path = sys.argv[1]
    teks = open(path).read()
    try:
        tree, tc = periksa(teks)
    except UnexpectedInput as e:
        print(f"{path}:{e.line}:{e.column}: GALAT SINTAKS")
        print(e.get_context(teks)); sys.exit(2)
    if "--tree" in sys.argv: print(tree.pretty())
    if "--trace" in sys.argv:
        for ln, tx in sorted(tc.log, key=lambda x: x[0]): print(f"  baris {ln:>2}  {tx}")
    for ln, kode, pesan in sorted(tc.errors):
        print(f"{path}:{ln}: {kode}: {pesan}")
    print(f"\n{len(tc.errors)} galat tipe/scope." if tc.errors else "\nTidak ada galat tipe.")
    sys.exit(1 if tc.errors else 0)
