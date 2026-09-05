"""Mesin perhitungan simulasi Insentif Service MFlash.

Dua peran saja: **Front Liner** (yang menyerahkan unit dan yang mengurus
faktur) dan **Store Leader**.

Sumber data: satu berkas CSV terkompresi (`.csv.gz`) berisi gabungan faktur
seluruh cabang, atau ekspor Excel per cabang.
"""
from __future__ import annotations

import glob
import gzip
import os
import re
import unicodedata

import pandas as pd

# Nama kolom baku di dalam aplikasi -> kemungkinan nama di berkas sumber.
PETA_KOLOM: dict[str, list[str]] = {
    "tanggal": ["TGL FAKTUR", "Tanggal Faktur", "Tanggal", "tanggal"],
    "no_faktur": ["NO FAKTUR", "No Faktur", "no_faktur"],
    "cabang": ["CABANG", "Nama Cabang", "NAMA CABANG", "Kode Cabang",
               "KODE CABANG", "cabang", "Toko", "OUTLET"],
    "kategori_pelanggan": ["KATEGORI PELANGGAN", "Kategori Pelanggan",
                           "kategori_pelanggan"],
    "kategori_penjualan": ["KATEGORI PENJUALAN", "Kategori Penjualan",
                           "kategori_penjualan"],
    "kategori_barang": ["KATEGORI BARANG", "Kategori Barang",
                        "kategori_barang"],
    "total_harga": ["TOTAL HARGA", "Total Harga", "total_harga"],
    "penyerah": ["YANG MENYERAHKAN/MENJUAL",
                 "Yang Menyerahkan/Menjual Faktur Penjualan",
                 "Yang Menyerahkan/Menjual", "penyerah"],
    "admin": ["NAMA ADMIN", "Nama Admin", "Admin", "admin"],
    "teknisi": ["NAMA TEKNISI (FINAL)", "Nama Teknisi (Final)",
                "NAMA TEKNISI", "Nama Teknisi", "teknisi"],
}

WAJIB = ["tanggal", "kategori_barang", "total_harga"]
BUKAN_NAMA = {"", "N/A", "NA", "-", "NULL", "NONE", "0", "NAN"}


def kunci(teks) -> str:
    """Normalkan nama supaya beda huruf besar/tanda baca tetap dianggap sama."""
    t = unicodedata.normalize("NFKD", str(teks or ""))
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _peta_balik() -> dict[str, str]:
    balik = {}
    for baku, kemungkinan in PETA_KOLOM.items():
        for n in kemungkinan:
            balik[kunci(n)] = baku
    return balik


def rapikan_kolom(df: pd.DataFrame) -> pd.DataFrame:
    """Ganti nama kolom sumber menjadi nama baku aplikasi."""
    balik = _peta_balik()
    ganti = {}
    for kol in df.columns:
        baku = balik.get(kunci(kol))
        if baku and baku not in ganti.values():
            ganti[kol] = baku
    df = df.rename(columns=ganti)
    kurang = [k for k in WAJIB if k not in df.columns]
    if kurang:
        raise ValueError(
            "Kolom wajib tidak ditemukan: " + ", ".join(kurang)
            + ". Kolom yang terbaca: " + ", ".join(map(str, df.columns[:20])))
    for opsional in ("cabang", "penyerah", "admin", "teknisi", "no_faktur",
                     "kategori_pelanggan", "kategori_penjualan"):
        if opsional not in df.columns:
            df[opsional] = ""
    return df


def _ke_angka(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        return s.fillna(0.0).astype(float)
    bersih = (s.astype(str)
               .str.replace(r"[Rp\s]", "", regex=True)
               .str.replace(".", "", regex=False)
               .str.replace(",", ".", regex=False))
    return pd.to_numeric(bersih, errors="coerce").fillna(0.0)


def _ke_tanggal(s: pd.Series) -> pd.Series:
    """Ubah kolom tanggal menjadi datetime.

    Tanggal ISO (2026-08-04) harus dibaca tahun-bulan-hari. Memakai
    dayfirst=True untuk semua nilai membuat tanggal ISO terbaca sebagai
    tahun-HARI-bulan, sehingga faktur satu bulan tersebar ke dua belas bulan.
    Jadi ISO dicoba lebih dulu, baru sisanya dibaca gaya Indonesia (04/08/2026).
    """
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    hasil = pd.to_datetime(s, errors="coerce", format="ISO8601")
    sisa = hasil.isna() & s.notna()
    if sisa.any():
        hasil.loc[sisa] = pd.to_datetime(s[sisa], errors="coerce",
                                         format="mixed", dayfirst=True)
    return hasil


def siapkan(df: pd.DataFrame) -> pd.DataFrame:
    """Bakukan kolom, tipe data, dan kolom bantu."""
    df = rapikan_kolom(df.copy())
    df["tanggal"] = _ke_tanggal(df["tanggal"])
    df = df[df["tanggal"].notna()]
    df["total_harga"] = _ke_angka(df["total_harga"])
    for k in ("cabang", "penyerah", "admin", "teknisi", "no_faktur",
              "kategori_pelanggan", "kategori_penjualan", "kategori_barang"):
        df[k] = df[k].fillna("").astype(str).str.strip()
    df["tahun"] = df["tanggal"].dt.year
    df["bulan"] = df["tanggal"].dt.month
    df["is_jasa"] = df["kategori_barang"].str.upper().eq("JASA")
    df["is_service"] = df["kategori_penjualan"].str.upper().str.startswith(
        "SERVICE")
    df["is_member"] = (df["kategori_pelanggan"].map(kunci)
                       == kunci("MEMBER REGULER"))
    df.loc[df["cabang"].eq(""), "cabang"] = "(tanpa nama cabang)"
    return df


# ------------------------------------------------------------------ memuat
def baca_berkas(sumber, nama: str = "") -> pd.DataFrame:
    """Baca satu berkas: .csv.gz, .csv, atau .xlsx/.xlsm."""
    nama = (nama or getattr(sumber, "name", "") or str(sumber)).lower()
    if nama.endswith((".csv.gz", ".gz")):
        return pd.read_csv(sumber, compression="gzip", low_memory=False)
    if nama.endswith(".csv"):
        return pd.read_csv(sumber, low_memory=False)
    return _baca_excel(sumber)


def _baca_excel(sumber) -> pd.DataFrame:
    """Ekspor Excel kadang menulis dimensi sheet yang salah dan menaruh data
    bukan di sheet pertama; keduanya ditangani di sini."""
    from openpyxl import load_workbook

    wb = load_workbook(sumber, data_only=True, read_only=True)
    balik = _peta_balik()
    try:
        for nama_sheet in wb.sheetnames:
            ws = wb[nama_sheet]
            ws._max_row = None
            ws._max_column = None
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            idx = None
            for i, r in enumerate(rows[:12]):
                baku = {balik.get(kunci(c)) for c in r if c is not None}
                if all(w in baku for w in WAJIB):
                    idx = i
                    break
            if idx is None:
                continue
            header = [str(c) if c is not None else f"_{j}"
                      for j, c in enumerate(rows[idx])]
            isi = [r for r in rows[idx + 1:]
                   if any(c is not None and str(c).strip() != "" for c in r)]
            return pd.DataFrame(isi, columns=header)
    finally:
        wb.close()
    raise ValueError("Tidak ada sheet yang memuat kolom Tanggal, Kategori "
                     "Barang, dan Total Harga.")


def muat_folder(folder: str = "data") -> pd.DataFrame:
    """Gabungkan semua berkas data di dalam folder repo."""
    berkas = sorted(glob.glob(os.path.join(folder, "*.csv.gz"))
                    + glob.glob(os.path.join(folder, "*.csv")))
    if not berkas:
        raise FileNotFoundError(
            f"Tidak ada berkas .csv.gz di folder '{folder}'. Jalankan "
            f"`python gabung.py <folder-ekspor>` untuk membuatnya.")
    bagian = [siapkan(baca_berkas(b, b)) for b in berkas]
    return pd.concat(bagian, ignore_index=True)


def tulis_csv_gz(df: pd.DataFrame, tujuan: str) -> str:
    """Simpan gabungan ke csv.gz, kolom sudah dibakukan."""
    kolom = ["tanggal", "no_faktur", "cabang", "kategori_pelanggan",
             "kategori_penjualan", "kategori_barang", "total_harga",
             "penyerah", "admin", "teknisi"]
    keluar = df[[k for k in kolom if k in df.columns]].copy()
    keluar["tanggal"] = pd.to_datetime(keluar["tanggal"]).dt.strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(tujuan) or ".", exist_ok=True)
    with gzip.open(tujuan, "wt", encoding="utf-8", newline="") as f:
        keluar.to_csv(f, index=False)
    return tujuan


# ------------------------------------------------------------------ hitung
def periode_tersedia(df: pd.DataFrame) -> list[tuple[int, int]]:
    p = df[["tahun", "bulan"]].drop_duplicates()
    return sorted((int(t), int(b)) for t, b in p.itertuples(index=False))[::-1]


def daftar_cabang(df: pd.DataFrame) -> list[str]:
    return sorted(df["cabang"].dropna().unique().tolist())


def _bersih(nama: str) -> str:
    return "" if str(nama).strip().upper() in BUKAN_NAMA else str(nama).strip()


def hitung(df: pd.DataFrame, bulan: int, tahun: int | None = None, *,
           cabang: list[str] | None = None,
           pct_teknisi: float = 30.0,
           hanya_member: bool = False,
           pct_pool: float = 2.0,
           porsi_front_liner: float = 80.0,
           porsi_store_leader: float = 20.0,
           bobot_penyerah: float = 60.0,
           nama_store_leader: dict[str, str] | None = None,
           pct_lama_team: float = 2.0) -> dict:
    """Hitung pool insentif service dan pembagiannya ke dua peran.

    Alur:
      1. Ambil baris jasa service pada periode dan cabang terpilih.
      2. Bagi hasil MFlash = omset jasa x (100% - bagi hasil teknisi).
      3. Pool insentif = bagi hasil MFlash x pct_pool.
      4. Pool dibagi ke Front Liner dan Store Leader menurut porsi.
      5. Bagian Front Liner dipecah pro-rata menurut kredit tiap orang.
         Satu baris jasa memberi kredit ke dua orang: yang menyerahkan unit
         (bobot_penyerah) dan yang mengurus faktur (sisanya). Bila salah satu
         namanya kosong, seluruh bobot jatuh ke yang ada.
      6. Bagian Store Leader dibagi rata antar cabang terpilih.
    """
    nama_store_leader = nama_store_leader or {}
    total_porsi = (porsi_front_liner + porsi_store_leader) or 1.0

    d = df[df["bulan"] == bulan]
    if tahun:
        d = d[d["tahun"] == tahun]
    if cabang:
        d = d[d["cabang"].isin(cabang)]

    baris_service = d[d["is_service"]]
    jasa = d[d["is_jasa"]]
    if hanya_member:
        jasa = jasa[jasa["is_member"]]

    omset_jasa = float(jasa["total_harga"].sum())
    omset_jasa_member = float(jasa.loc[jasa["is_member"], "total_harga"].sum())
    sparepart_service = float(
        baris_service.loc[baris_service["kategori_barang"].str.upper()
                          == "SPAREPART", "total_harga"].sum())

    # --- kredit Front Liner
    w_penyerah = max(0.0, min(100.0, bobot_penyerah)) / 100.0
    kredit: dict[tuple, float] = {}
    asli: dict[tuple, str] = {}
    peran_orang: dict[tuple, set] = {}
    tanpa_nama = 0.0

    # Kunci per (cabang, nama): orang bernama sama di dua cabang adalah dua
    # orang berbeda, dan hasilnya tetap jelas cabangnya.
    cabang_orang: dict[tuple, str] = {}
    for cab, pen, adm, nilai in zip(jasa["cabang"], jasa["penyerah"],
                                    jasa["admin"], jasa["total_harga"]):
        pen, adm = _bersih(pen), _bersih(adm)
        if not pen and not adm:
            tanpa_nama += float(nilai)
            continue
        bagi = [(pen, w_penyerah), (adm, 1 - w_penyerah)]
        if not adm:
            bagi = [(pen, 1.0)]
        elif not pen:
            bagi = [(adm, 1.0)]
        for nama, w in bagi:
            k = (cab, kunci(nama))
            kredit[k] = kredit.get(k, 0.0) + float(nilai) * w
            asli.setdefault(k, nama)
            cabang_orang.setdefault(k, cab)
            peran_orang.setdefault(k, set()).add(
                "penyerah" if nama == pen else "admin")

    bagi_hasil = omset_jasa * (100.0 - pct_teknisi) / 100.0
    pool = bagi_hasil * pct_pool / 100.0
    jatah_fl = pool * porsi_front_liner / total_porsi
    jatah_sl = pool * porsi_store_leader / total_porsi

    total_kredit = sum(kredit.values())
    front_liner = []
    for k, nilai in sorted(kredit.items(), key=lambda x: -x[1]):
        peran = peran_orang.get(k, set())
        label = ("Penyerah + Admin" if len(peran) > 1 else
                 "Penyerah" if "penyerah" in peran else "Admin")
        front_liner.append({
            "nama": asli[k], "cabang": cabang_orang.get(k, ""),
            "sebagai": label,
            "kredit_omset": round(nilai),
            "andil_pct": round(nilai / total_kredit * 100, 2) if total_kredit else 0.0,
            "insentif": round(jatah_fl * nilai / total_kredit) if total_kredit else 0,
        })

    cabang_dipakai = sorted(jasa["cabang"].unique().tolist()) or (cabang or [])
    per_cabang = (jasa.groupby("cabang")["total_harga"].sum().to_dict()
                  if not jasa.empty else {})
    sl = []
    for c in cabang_dipakai:
        sl.append({"cabang": c,
                   "nama": nama_store_leader.get(c, "Store Leader"),
                   "omset_jasa": round(per_cabang.get(c, 0.0)),
                   "insentif": round(jatah_sl / len(cabang_dipakai))
                   if cabang_dipakai else 0})

    bagi_hasil_member = omset_jasa_member * (100.0 - pct_teknisi) / 100.0
    lama = round(bagi_hasil_member * pct_lama_team / 100.0)

    return {
        "bulan": bulan, "tahun": tahun,
        "cabang": cabang_dipakai,
        "jumlah_baris": int(len(d)),
        "jumlah_faktur_service": int(baris_service["no_faktur"].nunique()),
        "omset_jasa": round(omset_jasa),
        "omset_jasa_member": round(omset_jasa_member),
        "omset_sparepart_service": round(sparepart_service),
        "pct_teknisi": pct_teknisi,
        "bagi_hasil_mflash": round(bagi_hasil),
        "pct_pool": pct_pool,
        "pool": round(pool),
        "bobot_penyerah": bobot_penyerah,
        "bagian": {"front_liner": round(jatah_fl),
                   "store_leader": round(jatah_sl)},
        "front_liner": front_liner,
        "store_leader": sl,
        "omset_tanpa_nama": round(tanpa_nama),
        "skema_lama": lama,
        "selisih": round(pool) - lama,
    }


def nama_mirip(nama_nama) -> list[tuple[str, str]]:
    """Pasangan nama yang satu memuat yang lain — kemungkinan orang yang sama
    dengan dua ejaan (mis. 'ARIF FIKRI' dan 'ARIF FIKRI KLENDER')."""
    semua = sorted(set(nama_nama))
    pasangan = []
    for i, a in enumerate(semua):
        for b in semua[i + 1:]:
            ka, kb = kunci(a), kunci(b)
            if ka != kb and (ka in kb or kb in ka):
                pasangan.append((a, b))
    return pasangan


def pct_netral_biaya(hasil: dict) -> float:
    """Tarif pool yang membuat biaya sama dengan skema lama."""
    dasar = hasil["bagi_hasil_mflash"]
    return round(hasil["skema_lama"] / dasar * 100.0, 3) if dasar else 0.0
