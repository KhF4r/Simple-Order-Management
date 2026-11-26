"""Uji otomatis untuk DSL NumType: tiap kasus punya daftar kode galat yang diharapkan."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lark.exceptions import UnexpectedInput
from checker import periksa

KASUS = [
 ("int + int valid",                    "int a = 1 + 2;",                                  []),
 ("int literal ke float (pelebaran)",   "float a = 3;",                                    []),
 ("float literal ke int (penyempitan)", "int a = 2.0;",                                    ["E-NARROW"]),
 ("int / int menghasilkan float",       "int a = 7 / 2;",                                  ["E-NARROW"]),
 ("int / int ke float valid",           "float a = 7 / 2;",                                []),
 ("str ke int",                         'int a = "1";',                                    ["E-MISMATCH"]),
 ("angka ke str",                       "str a = 1;",                                      ["E-MISMATCH"]),
 ("prioritas * di atas +",              "int a = 1 + 2 * 3;",                              []),
 ("kurung + campuran int/float",        "float a = (1 + 2) * 3.5;",                        []),
 ("asosiatif kiri a-b-c",               "int a = 10 - 3 - 2;",                             []),
 ("unary minus pada str",               'int a = -"x";',                                   ["E-OP"]),
 ("str + angka",                        'str a = "n=" + 1;',                               ["E-OP"]),
 ("str * angka",                        'str a = "ab" * 2;',                               ["E-OP"]),
 ("assign sebelum deklarasi",           "x = 5;",                                          ["E-UNDECL"]),
 ("deklarasi ganda",                    "int a = 1; int a = 2;",                           ["E-REDECL"]),
 ("tipe variabel statis (int<-float)",  "int a = 1; a = 2.5;",                             ["E-NARROW"]),
 ("fungsi: arity salah",                "fn f(float x) -> float; float y = f(1, 2);",      ["E-ARITY"]),
 ("fungsi: int ke param float OK",      "fn f(float x) -> float; float y = f(1);",         []),
 ("fungsi: float ke param int",         "fn f(int x) -> int; int y = f(1.5);",             ["E-NARROW"]),
 ("fungsi tak dideklarasikan",          "float y = g(1);",                                 ["E-UNDEF-FN"]),
 ("tanpa galat beruntun",               'int a = "x" + 1 * 2;',                            ["E-OP"]),
 ("identifier berawalan keyword",       "int integer = 1; float fn_x = integer;",          []),
]

gagal = 0
for nama, src, harap in KASUS:
    _, tc = periksa(src)
    dapat = sorted(k for _, k, _ in tc.errors)
    ok = dapat == sorted(harap)
    gagal += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {nama:<38} {dapat if dapat else '-'}" + ("" if ok else f"   (harap {harap})"))

# kasus sintaks: harus ditolak parser, bukan pemeriksa tipe
for nama, src in [("titik koma hilang", "int a = 1"), ("tipe tak dikenal", "double a = 1;"), ("ekspresi kosong", "int a = ;")]:
    try:
        periksa(src); ok = False
    except UnexpectedInput:
        ok = True
    gagal += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {'sintaks: ' + nama:<38} ditolak parser")

total = len(KASUS) + 3
print(f"\n{total - gagal}/{total} lulus")
sys.exit(1 if gagal else 0)
