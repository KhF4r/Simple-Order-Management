"""No.2: bandingkan parse tree "tertulis" (CFG buku teks, Lark) dengan parse tree Tree-sitter.

Tiap fragmen dikerjakan 3 cara:
  (1) pohon turunan CFG (semua nonterminal + token),
  (2) derivasi leftmost langkah demi langkah,
  (3) normalisasi ke kosakata Tree-sitter lalu dibandingkan otomatis dengan pohon Tree-sitter asli.
"""
import os, sys
from lark import Lark, Tree, Token
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

SRC = open(sys.argv[1], "rb").read()
TS = Parser(Language(tspython.language())).parse(SRC).root_node
CFG = Lark(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tertulis.lark")).read(), parser="lalr", keep_all_tokens=True,
           start=["header", "paramlist", "stmt"])

# ---------- utilitas pohon Tree-sitter ----------
def ts_cari(node, tipe, teks):
    if node.type == tipe and node.text.decode() == teks:
        return node
    for c in node.children:
        h = ts_cari(c, tipe, teks)
        if h: return h

def ts_norm(n):
    """Kosakata Tree-sitter, hanya node bernama; string dilipat jadi daun."""
    if n.type == "string" or not n.named_children:
        return (n.type, n.text.decode())
    return (n.type, *[ts_norm(c) for c in n.named_children])

def ts_stat(n, semua):
    jml, dalam = 0, 0
    def r(x, d):
        nonlocal jml, dalam
        if semua or x.is_named:
            jml += 1; dalam = max(dalam, d)
            d += 1
        for c in x.children: r(c, d)
    r(n, 0)
    return jml, dalam

# ---------- utilitas pohon CFG ----------
def cfg_stat(t, hanya_nonterminal=False):
    jml, dalam = 0, 0
    def r(x, d):
        nonlocal jml, dalam
        if isinstance(x, Token):
            if not hanya_nonterminal:
                jml += 1; dalam = max(dalam, d)
            return
        jml += 1; dalam = max(dalam, d)
        for c in x.children: r(c, d + 1)
    r(t, 0)
    return jml, dalam

def cfg_cetak(t, d=0, out=None):
    out = out if out is not None else []
    if isinstance(t, Token):
        out.append("  " * d + f'"{t}"')
    else:
        out.append("  " * d + f"<{t.data}>")
        for c in t.children: cfg_cetak(c, d + 1, out)
    return out

def leftmost(t):
    """Hasilkan derivasi leftmost: daftar (aturan_dipakai, bentuk_kalimat)."""
    def sym(x): return f"<{x.data}>" if isinstance(x, Tree) else str(x)
    form, langkah = [t], [(None, f"<{t.data}>")]
    while True:
        i = next((k for k, x in enumerate(form) if isinstance(x, Tree)), None)
        if i is None: break
        x = form[i]
        form[i:i + 1] = x.children
        aturan = f"{x.data} → " + " ".join(sym(c) if isinstance(c, Tree) else f'"{c}"' for c in x.children)
        langkah.append((aturan, " ".join(sym(c) for c in form)))
    return langkah

def flat_list(t, nama):
    """Ratakan rekursi kanan: paramlist/arglist -> daftar elemen."""
    hasil = []
    while True:
        hasil.append(t.children[0])
        if len(t.children) == 1: return hasil
        t = t.children[2]          # [elem, ",", sisa]

def cfg_norm(x):
    """Lipat pohon CFG ke kosakata Tree-sitter (hapus rantai unit & rekursi kanan)."""
    if isinstance(x, Token):
        if x.type == "NAME": return ("identifier", str(x))
        if x.type == "NUMBER": return ("float" if "." in x else "integer", str(x))
        if x.type == "STRING": return ("string", str(x))
        return None
    d = x.data
    if d == "paramlist": return ("parameters", *[cfg_norm(p) for p in flat_list(x, d)])
    if d == "arglist":   return ("argument_list", *[cfg_norm(p) for p in flat_list(x, d)])
    if d == "param":
        return ("typed_parameter", cfg_norm(x.children[0]), cfg_norm(x.children[2])) if len(x.children) == 3 \
               else cfg_norm(x.children[0])
    if d == "type":   return ("type", cfg_norm(x.children[0]))
    if d == "stmt":   return ("expression_statement", cfg_norm(x.children[0]))
    if d == "assign": return ("assignment", cfg_norm(x.children[0]), cfg_norm(x.children[2]))
    if d in ("expr", "term"):
        if len(x.children) == 1: return cfg_norm(x.children[0])
        return ("binary_operator", cfg_norm(x.children[0]), cfg_norm(x.children[2]))
    if d == "factor": return cfg_norm(x.children[0])
    if d == "atom":
        c = x.children
        if len(c) == 1: return cfg_norm(c[0])
        if str(c[1]) == ".": return ("attribute", cfg_norm(c[0]), cfg_norm(c[2]))
        return ("call", cfg_norm(c[0]), cfg_norm(c[2]))
    raise ValueError(d)

# ---------- fragmen yang dibandingkan ----------
FRAGMEN = [
    ("F1  parameter __init__ Product  (parameter dengan tipe primitif)",
     "paramlist", "self, product_id: int, name: str, price: float",
     lambda: ts_cari(TS, "parameters", "(self, product_id: int, name: str, price: float)")),
    ("F2  parameter add_item  (parameter bertipe OBJEK: Product)",
     "paramlist", "self, product: Product, quantity: int",
     lambda: ts_cari(TS, "parameters", "(self, product: Product, quantity: int)")),
    ("F3  tax = self.total * tax_rate  (ekspresi, rantai Expr→Term→Factor→Atom)",
     "stmt", "tax = self.total * tax_rate",
     lambda: ts_cari(TS, "expression_statement", "tax = self.total * tax_rate")),
    ('F4  product1 = Product(101, "Laptop", 7500000)  (argumen pembuatan objek)',
     "stmt", 'product1 = Product(101, "Laptop", 7500000)',
     lambda: ts_cari(TS, "expression_statement", 'product1 = Product(101, "Laptop", 7500000)')),
]

def main():
    ringkas = []
    for judul, start, teks, ambil in FRAGMEN:
        print("\n" + "#" * 78 + f"\n# {judul}\n" + "#" * 78)
        cfg = CFG.parse(teks, start=start)
        ts = ambil()
        assert ts is not None, "node Tree-sitter tidak ditemukan"

        print("\n[1] Pohon turunan CFG buku teks (nonterminal <...>, token \"...\"):")
        print("\n".join(cfg_cetak(cfg)))

        print("\n[2] Pohon Tree-sitter (node bernama, + field):")
        def tampil(n, d=0, f=None):
            if not n.is_named: return
            lab = f"{f}: " if f else ""
            ekor = f"  «{n.text.decode()}»" if (n.type == "string" or not n.named_children) else ""
            print("  " * d + f"{lab}{n.type}{ekor}")
            if n.type == "string": return
            for i, c in enumerate(n.children): tampil(c, d + 1, n.field_name_for_child(i))
        tampil(ts)

        a, b = cfg_norm(cfg), ts_norm(ts)
        print(f"\n[3] Setelah CFG dilipat ke kosakata Tree-sitter, struktur identik? → {a == b}")
        if a != b:
            print("   CFG :", a); print("   TS  :", b)

        sn, sd = cfg_stat(cfg); nn, nd = cfg_stat(cfg, True)
        tn, td = ts_stat(ts, False); fn, fd = ts_stat(ts, True)
        print("\n[4] Ukuran pohon:")
        print(f"    CFG buku teks (nonterminal+token) : {sn:3d} node, kedalaman {sd}")
        print(f"    CFG buku teks (nonterminal saja)  : {nn:3d} node, kedalaman {nd}")
        print(f"    Tree-sitter node bernama          : {tn:3d} node, kedalaman {td}")
        print(f"    Tree-sitter CST lengkap           : {fn:3d} node, kedalaman {fd}")
        ringkas.append((judul.split("  ")[0], sn, sd, tn, td, fn, fd, a == b))

    # derivasi leftmost lengkap untuk header fungsi (parsing parameter)
    print("\n" + "#" * 78 + "\n# DERIVASI LEFTMOST: def __init__(self, product_id: int, name: str, price: float):\n" + "#" * 78)
    hdr = CFG.parse("def __init__(self, product_id: int, name: str, price: float):", start="header")
    for i, (aturan, bentuk) in enumerate(leftmost(hdr)):
        print(f"{i:2d}. {'⇒ ' if i else '   '}{bentuk}")
        if aturan: print(f"      memakai: {aturan}")

    print("\n" + "#" * 78 + "\n# DERIVASI LEFTMOST: product1 = Product(101, \"Laptop\", 7500000)\n" + "#" * 78)
    d = leftmost(CFG.parse('product1 = Product(101, "Laptop", 7500000)', start="stmt"))
    print(f"(panjang derivasi: {len(d)-1} langkah; 12 langkah pertama ditampilkan)")
    for i, (aturan, bentuk) in enumerate(d[:13]):
        print(f"{i:2d}. {'⇒ ' if i else '   '}{bentuk}")

    print("\n" + "#" * 78 + "\n# RINGKASAN\n" + "#" * 78)
    print(f"{'frag':5} {'CFG':>10} {'TS bernama':>12} {'TS lengkap':>12}  identik")
    for f, sn, sd, tn, td, fn, fd, ok in ringkas:
        print(f"{f:5} {sn:>5}/d{sd:<3} {tn:>7}/d{td:<3} {fn:>7}/d{fd:<3}  {ok}")

main()
