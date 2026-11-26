"""No.3: analisis semantik (tipe & scope) memakai code analyzer Python, dikaitkan ke parse tree.

  symtable  -> tabel scope bawaan Python (+ pemeriksa scope mini buatan sendiri)
  pyflakes  -> nama tak terdefinisi, import tak terpakai
  mypy      -> pemeriksaan tipe statis
  pylint    -> pemeriksaan umum (undefined-variable, no-member, dst.)
  eksekusi  -> bukti nyata bahwa temuan/kelolosan analyzer memang bug
Lalu tiap temuan dipetakan ke node Tree-sitter terkecil yang melingkupinya.
"""
import ast, os, builtins, importlib.util, json, re, subprocess, sys, symtable
from pyflakes.checker import Checker
from mypy import api as mypy_api
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

FILE = sys.argv[1]
SRC = open(FILE).read()
TS = Parser(Language(tspython.language())).parse(SRC.encode()).root_node


def judul(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# ------------------------------------------------------------------ A. symtable
judul("A. SCOPE: tabel simbol (symtable) + pemeriksa scope mini")
modul = symtable.symtable(SRC, FILE, "exec")

def dump(tbl, d=0):
    ind = "  " * d
    print(f"{ind}[{tbl.get_type()}] {tbl.get_name()}  (baris {tbl.get_lineno()})")
    for s in tbl.get_symbols():
        if tbl.get_type() == "function":
            peran = []
            if s.is_parameter(): peran.append("parameter")
            elif s.is_assigned(): peran.append("lokal")
            if s.is_global() and s.is_referenced() and not s.is_assigned(): peran.append("GLOBAL (dibaca)")
            if peran: print(f"{ind}    {s.get_name():<14} {', '.join(peran)}")
    for c in tbl.get_children(): dump(c, d + 1)
dump(modul)

# nama yang boleh dirujuk dari fungsi: simbol modul yang di-assign/import/def/class + builtin
tersedia = {s.get_name() for s in modul.get_symbols() if s.is_assigned() or s.is_imported() or s.is_namespace()}
tersedia |= set(dir(builtins))

scope_findings = []
def cek_scope(tbl):
    for s in tbl.get_symbols():
        if tbl.get_type() == "function" and s.is_global() and s.is_referenced() and not s.is_assigned() \
           and s.get_name() not in tersedia:
            scope_findings.append((s.get_name(), tbl.get_name()))
    for c in tbl.get_children(): cek_scope(c)
cek_scope(modul)
print("\nPemeriksa scope mini (simbol GLOBAL yang dibaca tapi tidak pernah didefinisikan):")
for nama, fn in scope_findings:
    print(f"   ✗ '{nama}' dirujuk di {fn}() tapi tidak ada di scope modul maupun builtin")

# ------------------------------------------------------------------ B. analyzer
temuan = []   # (alat, baris, kolom0, kode, pesan)
for m in Checker(ast.parse(SRC), FILE).messages:
    temuan.append(("pyflakes", m.lineno, m.col, type(m).__name__, m.message % m.message_args))

out, _, _ = mypy_api.run(["--check-untyped-defs", "--show-column-numbers", "--show-error-codes",
                          "--no-error-summary", FILE])
for ln in out.splitlines():
    m = re.match(r".+?:(\d+):(\d+): error: (.*?)\s+\[(.+)\]$", ln)
    if m: temuan.append(("mypy", int(m[1]), int(m[2]) - 1, m[4], m[3]))

pl = subprocess.run([sys.executable, "-m", "pylint", "--disable=C,R", "--output-format=json", FILE],
                    capture_output=True, text=True).stdout
for m in json.loads(pl or "[]"):
    temuan.append(("pylint", m["line"], m["column"], m["symbol"], m["message"]))

temuan.sort(key=lambda t: (t[1], t[0]))
json.dump(temuan, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "temuan.json"), "w"))
judul("B. TEMUAN CODE ANALYZER (diurutkan per baris)")
print(f"{'baris':>5}  {'alat':<9} {'kode':<20} pesan")
for alat, b, k, kode, pesan in temuan:
    print(f"{b:>5}  {alat:<9} {kode:<20} {pesan}")

# ------------------------------------------------------------------ C. kaitkan ke parse tree
judul("C. KAITAN KE PARSE TREE: node Tree-sitter terkecil pada posisi tiap temuan")
def rantai(b, k):
    n = TS.descendant_for_point_range((b - 1, k), (b - 1, k + 1))
    while n is not None and not n.is_named: n = n.parent
    jalur = []
    while n is not None:
        jalur.append(n.type); n = n.parent
    return jalur
seen = set()
for alat, b, k, kode, pesan in temuan:
    kunci = (b, k)
    if kunci in seen: continue
    seen.add(kunci)
    j = rantai(b, k)
    print(f"baris {b}:{k}  {'  ←  '.join(j[:6])}{'  ← ...' if len(j) > 6 else ''}")

# ------------------------------------------------------------------ D. bukti eksekusi
judul("D. BUKTI EKSEKUSI: apakah tiap dugaan bug benar-benar gagal saat dijalankan?")
spec = importlib.util.spec_from_file_location("order_mod", FILE)
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
from types import SimpleNamespace as NS

def siapkan():
    svc = M.OrderService(); o = svc.create_order("A"); o.add_item(M.Product(1, "x", 1000.0), 2); return svc, o

kasus = {
    "B2 baris 41  calculate_tax(\"0.11\")  str → float": lambda: M.Order("A").calculate_tax("0.11"),
    "B3 baris 46  order.id tidak ada di Order":          lambda: siapkan()[0].find_order(1),
    "B4 baris 57  order_status tak terdefinisi":         lambda: siapkan()[0].generate_report(),
    "B5 baris 64  product.quantity (objek Product)":     lambda: M.calculate_bulk_price([M.Product(1, "x", 1.0)], 0),
    "B7 baris 67  \"Total: \" + total":                  lambda: M.calculate_bulk_price([NS(price=2.0, quantity=3)], 0),
    "B*  main()  (alur program utuh)":                   lambda: M.main(),
}
bukti = {}
for nama, fn in kasus.items():
    try:
        r = fn(); print(f"  OK   {nama:<52} → {r!r}"); bukti[nama[:2]] = False
    except Exception as e:
        print(f"  GAGAL {nama:<51} → {type(e).__name__}: {e}"); bukti[nama[:2]] = True

# B6: int -> float pada variabel yang sama (benar di runtime, salah di mata type checker)
total = 0; sebelum = type(total).__name__; total = total - 0.5
print(f"  OK   B6 baris 66  total=0 lalu total-discount             → tipe {sebelum} berubah jadi {type(total).__name__} (tidak crash, tetapi tipe tidak konsisten)")

# ------------------------------------------------------------------ E. matriks
judul("E. MATRIKS: bug nyata vs siapa yang menemukannya")
bug = [("B1", 10, "items = []  tanpa anotasi tipe", None),
       ("B2", 41, "argumen str untuk parameter float", "B2"),
       ("B3", 46, "order.id (atribut tidak ada)", "B3"),
       ("B4", 57, "order_status tak terdefinisi", "B4"),
       ("B5", 64, "product.quantity (atribut tidak ada)", "B5"),
       ("B6", 66, "total int lalu diisi float", None),
       ("B7", 67, "str + angka (& return str, deklarasi float)", "B7")]
alat_list = ["pyflakes", "mypy", "pylint"]
print(f"{'id':<3} {'baris':>5}  {'bug':<44} " + " ".join(f"{a:^9}" for a in alat_list) + "  runtime")
for bid, b, desk, kunci in bug:
    sel = []
    for a in alat_list:
        sel.append("✓" if any(t[0] == a and t[1] == b for t in temuan) else "–")
    rt = "crash" if (kunci and bukti.get(kunci)) else ("tidak crash" if kunci is None else "?")
    print(f"{bid:<3} {b:>5}  {desk:<44} " + " ".join(f"{s:^9}" for s in sel) + f"  {rt}")
