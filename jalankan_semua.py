"""Menjalankan semua tugas berurutan dan menyimpan outputnya. Pakai:  python jalankan_semua.py"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
KODE = os.path.join("..", "simple_order_management.py")
LANGKAH = [
    ("No.1 parse tree",            "01_parse",    ["parse_tree.py", KODE],                "parse_tree_output.txt"),
    ("No.2 banding + derivasi",    "02_banding",  ["banding.py", KODE],                   "banding_output.txt"),
    ("No.3 analisis semantik",     "03_semantik", ["analisis.py", "simple_order_management.py"], "analisis_output.txt"),
    ("No.4 uji DSL Lark",          "04_lark",     ["uji_dsl.py"],                         "uji_dsl_output.txt"),
    ("No.4 DSL pada model order",  "04_lark",     ["checker.py", "contoh/order_bugs.num"], "order_bugs_output.txt"),
    ("No.4 banding No.3 vs No.4",  "04_lark",     ["banding_no3_no4.py"],                 "banding_no3_no4_output.txt"),
]
for nama, folder, args, keluar in LANGKAH:
    r = subprocess.run([sys.executable, "-I", *args], cwd=os.path.join(ROOT, folder), capture_output=True, text=True)
    open(os.path.join(ROOT, folder, keluar), "w", encoding="utf-8").write(r.stdout + r.stderr)
    # checker.py sengaja exit 1 (ada galat di program uji); yang dianggap gagal hanya exit>1 / traceback
    ok = r.returncode in (0, 1) and "Traceback" not in r.stderr
    print(f"{'OK  ' if ok else 'GAGAL'} {nama:<30} → {folder}/{keluar}")
