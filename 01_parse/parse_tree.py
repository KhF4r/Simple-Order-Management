"""No.1: parse simple_order_management.py dengan Tree-sitter dan cetak parse tree.

Pakai:  python parse_tree.py ../simple_order_management.py
Output: 3 tampilan (S-expression, pohon bernama berindentasi, CST lengkap dengan token anonim)
"""
import sys
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

parser = Parser(Language(tspython.language()))


def tampil(node, kedalaman=0, field=None, semua=False, teks=True):
    """Cetak pohon. semua=False -> hanya node bernama; semua=True -> CST lengkap."""
    if not semua and not node.is_named:
        return
    baris, kolom = node.start_point
    akhir_b, akhir_k = node.end_point
    label = f"{field}: " if field else ""
    jenis = node.type if node.is_named else f'"{node.type}"'
    ekor = ""
    if teks and node.child_count == 0:          # daun: tampilkan teksnya
        ekor = f"   «{node.text.decode()}»"
    print("  " * kedalaman + f"{label}{jenis} [{baris+1}:{kolom}-{akhir_b+1}:{akhir_k}]{ekor}")
    for i, anak in enumerate(node.children):
        tampil(anak, kedalaman + 1, node.field_name_for_child(i), semua, teks)


def statistik(root):
    nama = anon = 0
    stack = [root]
    while stack:
        n = stack.pop()
        if n.is_named: nama += 1
        else: anon += 1
        stack.extend(n.children)
    return nama, anon


if __name__ == "__main__":
    src = open(sys.argv[1], "rb").read()
    tree = parser.parse(src)
    root = tree.root_node

    print("=" * 70, "\n[A] S-expression (format bawaan Tree-sitter)\n", "=" * 70, sep="")
    print(root)

    print("\n" + "=" * 70, "\n[B] Pohon node bernama, berindentasi + field + posisi baris:kolom\n", "=" * 70, sep="")
    tampil(root)

    print("\n" + "=" * 70, "\n[C] CST lengkap termasuk token anonim: hanya method Order.calculate_tax\n", "=" * 70, sep="")
    for cls in root.named_children:
        if cls.type == "class_definition" and cls.child_by_field_name("name").text == b"Order":
            for m in cls.child_by_field_name("body").named_children:
                if m.child_by_field_name("name").text == b"calculate_tax":
                    tampil(m, semua=True)

    nama, anon = statistik(root)
    print("\n" + "=" * 70, "\n[D] Ringkasan\n", "=" * 70, sep="")
    print(f"has_error         : {root.has_error}")
    print(f"node bernama      : {nama}")
    print(f"node anonim       : {anon}")
    print(f"total node        : {nama + anon}")
    print(f"jumlah baris kode : {root.end_point[0]}")
