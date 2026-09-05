"""Gabungkan ekspor faktur per cabang menjadi satu berkas csv.gz.

Pakai sekali setiap kali ada data bulan baru, lalu commit hasilnya ke GitHub.

    python gabung.py <folder-ekspor> [-o data/faktur-gabungan.csv.gz]

Nama cabang diambil dari kolom cabang bila ada; kalau tidak ada, dari nama
berkasnya. Jadi beri nama berkas seperti `klender.xlsx`, `bintara.xlsx`,
atau `faktur_klender_2026-08.xlsx`.
"""
import argparse
import glob
import os
import re
import sys

import pandas as pd

import insentif as ins


def tebak_cabang(path: str) -> str:
    """Ambil nama cabang dari nama berkas."""
    dasar = os.path.basename(path)
    dasar = re.sub(r"\.(csv\.gz|csv|xlsx|xlsm)$", "", dasar, flags=re.I)
    dasar = re.sub(r"(rincian|faktur|penjualan|export|ekspor|data)", " ",
                   dasar, flags=re.I)
    dasar = re.sub(r"[\d_\-]+", " ", dasar)
    return " ".join(dasar.split()).title() or "Tanpa Nama"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", help="folder berisi ekspor per cabang")
    p.add_argument("-o", "--keluaran", default="data/faktur-gabungan.csv.gz")
    a = p.parse_args()

    berkas = sorted(sum([glob.glob(os.path.join(a.folder, f"*.{e}"))
                         for e in ("xlsx", "xlsm", "csv", "csv.gz")], []))
    if not berkas:
        print(f"Tidak ada berkas ekspor di '{a.folder}'.", file=sys.stderr)
        return 1

    bagian, ringkas = [], []
    for b in berkas:
        try:
            df = ins.siapkan(ins.baca_berkas(b, b))
        except Exception as e:  # noqa: BLE001
            print(f"  LEWAT  {os.path.basename(b)}: {e}", file=sys.stderr)
            continue
        kosong = df["cabang"].eq("(tanpa nama cabang)")
        if kosong.any():
            df.loc[kosong, "cabang"] = tebak_cabang(b)
        df["_sumber"] = os.path.basename(b)
        bagian.append(df)
        ringkas.append((os.path.basename(b), df["cabang"].iloc[0], len(df)))
        print(f"  OK     {os.path.basename(b)} -> {df['cabang'].iloc[0]} "
              f"({len(df):,} baris)".replace(",", "."))

    if not bagian:
        print("Tidak ada berkas yang berhasil dibaca.", file=sys.stderr)
        return 1

    gabungan = pd.concat(bagian, ignore_index=True)

    # Baris kembar TIDAK dibuang. Satu faktur wajar memuat dua baris identik
    # (mis. dua sparepart sama harga), dan membuangnya mengurangi omset yang
    # sah — pada data uji selisihnya Rp 1,2 juta. Yang diperiksa hanya apakah
    # satu cabang-periode masuk dua kali, tanda berkas terunggah ganda.
    ganda = (gabungan.assign(_b=gabungan["tanggal"].dt.to_period("M"))
             .groupby(["cabang", "_b"])["_sumber"].nunique())
    ganda = ganda[ganda > 1]
    if not ganda.empty:
        print("\nPERINGATAN: cabang-periode berikut ada di lebih dari satu "
              "berkas, kemungkinan terhitung dobel:", file=sys.stderr)
        for (c, b), n in ganda.items():
            print(f"  - {c} {b} ({n} berkas)", file=sys.stderr)

    ins.tulis_csv_gz(gabungan, a.keluaran)
    ukuran = os.path.getsize(a.keluaran) / 1_048_576
    print(f"\n{len(gabungan):,} baris".replace(",", ".")
          + f" -> {a.keluaran} ({ukuran:.1f} MB)")
    print(f"Cabang: {', '.join(sorted(gabungan['cabang'].unique()))}")
    print(f"Periode: {gabungan['tanggal'].min():%b %Y} "
          f"s.d. {gabungan['tanggal'].max():%b %Y}")
    if ukuran > 90:
        print("\nPERINGATAN: berkas mendekati batas 100 MB per file di GitHub. "
              "Pecah per tahun bila perlu.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
