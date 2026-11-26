# Tugas Manajemen Order: Tree-sitter, Analisis Semantik, DSL Lark

## Isi folder
| Folder / file | Isi |
|---|---|
| `simple_order_management_ASLI.py` | File dari soal, **tanpa indentasi** (tidak bisa di-parse dengan benar) |
| `simple_order_management.py` | File yang sama dengan indentasi dipulihkan (isi kode identik) |
| `01_parse/` | No.1 parse tree Tree-sitter |
| `02_banding/` | No.2 pohon tertulis (CFG) vs Tree-sitter + derivasi leftmost |
| `03_semantik/` | No.3 symtable, pyflakes, mypy, pylint + bukti eksekusi |
| `04_lark/` | No.4 grammar EBNF Lark, pemeriksa tipe, uji, perbandingan |
| `jalankan_semua.py` | Menjalankan semuanya sekaligus |

## Setup di VS Code (Windows)

1. Pasang Python 3.10 sampai 3.13 dari python.org. Centang **"Add python.exe to PATH"**.
2. Buka folder ini lewat **File → Open Folder**, lalu buka terminal (`Ctrl+` `).
3. Buat virtualenv dan pasang paket. Tidak perlu compiler C dan tidak perlu `tree-sitter-cli`:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
4. `Ctrl+Shift+P` → **Python: Select Interpreter** → pilih `.venv`.

### Kalau muncul tulisan merah
| Pesan | Penyebab | Solusi |
|---|---|---|
| `running scripts is disabled on this system` (saat `activate` atau `npm`) | PowerShell memblokir skrip | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, atau ganti terminal ke **Command Prompt** |
| `'python' is not recognized` / `pip is not recognized` | Python tidak ada di PATH | Pakai `py -m pip ...` dan `py file.py`, atau pasang ulang Python dengan opsi PATH |
| `ModuleNotFoundError: tree_sitter_python` | Paket terpasang di Python lain | Aktifkan `.venv`, pasang ulang dengan `python -m pip install ...` |
| `AttributeError: ... set_language` / `build_library` | Tutorial lama memakai API versi lama | Pakai gaya baru: `Parser(Language(tspython.language()))` |
| `Microsoft Visual C++ 14.0 is required` | Pip mencoba mengompilasi karena tidak ada wheel untuk versi Python Anda | Pakai Python 3.12 atau 3.13, lalu `pip install --upgrade pip` |
| `TypeError` soal bytes | `parser.parse()` butuh bytes | `b"..."` atau `teks.encode()` |

## Cara menjalankan
Jalankan dari terminal VS Code (virtualenv aktif). Semua skrip bisa dipanggil dari folder mana pun.

```powershell
python jalankan_semua.py                                 # semuanya, output tersimpan di tiap folder

cd 01_parse;    python parse_tree.py ..\simple_order_management.py            # No.1
cd ..\02_banding; python banding.py ..\simple_order_management.py             # No.2
cd ..\03_semantik; python analisis.py simple_order_management.py              # No.3
cd ..\04_lark;  python checker.py contoh\order_bugs.num                       # No.4 (DSL)
python checker.py contoh\order_bugs.num --tree --trace   # pohon DSL + jejak tipe
python uji_dsl.py                                        # 25 uji otomatis
python banding_no3_no4.py                                # perbandingan No.3 vs No.4
```

Perintah analyzer satu per satu (No.3):
```powershell
python -m pyflakes simple_order_management.py
python -m mypy --check-untyped-defs simple_order_management.py
python -m pylint --disable=C,R simple_order_management.py
```

## Tree-sitter untuk Java
```python
import tree_sitter_java as tsj
from tree_sitter import Language, Parser
parser = Parser(Language(tsj.language()))
print(parser.parse(b"class A { double f(double x) { return x * 2; } }").root_node)
```
