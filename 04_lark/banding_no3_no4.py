"""Bandingkan hasil No.3 (code analyzer Python) dengan No.4 (DSL Lark).

Eksperimen tambahan: tambahkan anotasi tipe yang kurang pada kode Python, jalankan mypy lagi,
untuk membuktikan mengapa B3 dan B5 sebelumnya lolos.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mypy import api as mypy_api
from checker import periksa

D3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "03_semantik")
temuan = json.load(open(os.path.join(D3, "temuan.json")))     # [alat, baris, kolom, kode, pesan]

# ---- eksperimen: mypy pada kode yang dilengkapi anotasi tipe -----------------------------
asli = open(os.path.join(D3, "simple_order_management.py")).read()
anot = (asli.replace("self.orders = []", "self.orders: list[Order] = []")
            .replace("self.items = []", "self.items: list[dict[str, object]] = []")
            .replace("products: list,", "products: list[Product],"))
p_anot = os.path.join(D3, "simple_order_management_annotated.py")
open(p_anot, "w").write(anot)
out, _, _ = mypy_api.run(["--check-untyped-defs", "--show-error-codes", "--no-error-summary", p_anot])
mypy_anot = []
for ln in out.splitlines():
    m = re.match(r".+?:(\d+): error: (.*?)\s+\[(.+)\]$", ln)
    if m: mypy_anot.append((int(m[1]), m[3], m[2]))

print("=" * 78 + "\nEKSPERIMEN: mypy setelah anotasi tipe dilengkapi\n" + "=" * 78)
print("Perubahan: self.orders: list[Order],  self.items: list[dict[str, object]],  products: list[Product]\n")
base = {(t[1], t[3]) for t in temuan if t[0] == "mypy"}
for b, kode, pesan in sorted(mypy_anot):
    tanda = "  ← BARU" if (b, kode) not in base else ""
    print(f"  baris {b:>2}  {kode:<14} {pesan}{tanda}")

# ---- DSL: petakan galat ke ID bug lewat penanda [Bx] di komentar ------------------------
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contoh", "order_bugs.num")
baris = open(path).read().splitlines()
_, tc = periksa("\n".join(baris))
dsl = set()
for ln, kode, pesan in tc.errors:
    m = re.search(r"\[(B\d)\]", baris[ln - 1])
    if m: dsl.add(m[1])

# ---- matriks ------------------------------------------------------------------------------
bug = [("B1", 10, "items = []  tanpa anotasi tipe"),
       ("B2", 41, "str dikirim ke parameter float"),
       ("B3", 46, "order.id (atribut tidak ada)"),
       ("B4", 57, "order_status tak terdefinisi"),
       ("B5", 64, "product.quantity (atribut tidak ada)"),
       ("B6", 66, "variabel int diisi float"),
       ("B7", 67, "str + angka")]
def ada(alat, b): return any(t[0] == alat and t[1] == b for t in temuan)
NA = {"B1": "n/a¹", "B3": "n/a²", "B5": "n/a²"}
print("\n" + "=" * 78 + "\nMATRIKS PERBANDINGAN No.3 vs No.4  (✓ terdeteksi, – lolos, n/a di luar jangkauan)\n" + "=" * 78)
kolom = ["pyflakes", "mypy", "pylint", "mypy+anotasi", "DSL Lark"]
print(f"{'id':<3} {'baris':>5} {'bug':<38}" + "".join(f"{k:>14}" for k in kolom))
jumlah = {k: 0 for k in kolom}
for bid, b, desk in bug:
    sel = [ada("pyflakes", b), ada("mypy", b), ada("pylint", b), any(x[0] == b for x in mypy_anot),
           (bid in dsl) if bid not in NA else NA[bid]]
    row = ""
    for k, v in zip(kolom, sel):
        if isinstance(v, str): row += f"{v:>14}"
        else:
            row += f"{'✓' if v else '–':>14}"; jumlah[k] += bool(v)
    print(f"{bid:<3} {b:>5} {desk:<38}{row}")
print(f"{'jumlah terdeteksi':<47}" + "".join(f"{jumlah[k]:>14}" for k in kolom))
print("\n¹ Grammar DSL mewajibkan tipe eksplisit di tiap deklarasi, jadi 'lupa anotasi' tidak bisa terjadi.")
print("² DSL ini tidak punya konsep objek/atribut, sehingga bug atribut tidak dapat dinyatakan.")
