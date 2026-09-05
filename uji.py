"""Uji cepat mesin perhitungan tanpa perlu berkas Excel.

Jalankan: python uji.py
"""
import insentif as ins


def faktur_contoh():
    """Dua faktur service: satu Rp 300rb (Andi/Budi), satu Rp 100rb (Andi/Citra)."""
    def baris(no, kat_barang, nilai, sales, admin, member=True):
        return {ins.kunci("TGL FAKTUR"): __import__("datetime").date(2026, 8, 5),
                ins.kunci("NO FAKTUR"): no,
                ins.kunci("KATEGORI BARANG"): kat_barang,
                ins.kunci("KATEGORI PENJUALAN"): "SERVICE HP",
                ins.kunci("KATEGORI PELANGGAN"):
                    "Member Reguler" if member else "Umum",
                ins.kunci("TOTAL HARGA"): nilai,
                ins.kunci("YANG MENYERAHKAN/MENJUAL"): sales,
                ins.kunci("NAMA ADMIN"): admin}
    return [
        baris("F1", "JASA", 300_000, "Andi", "Budi"),
        baris("F1", "SPAREPART", 50_000, "Andi", "Budi"),
        baris("F2", "JASA", 100_000, "Andi", "Citra", member=False),
    ]


def cek(nama, dapat, harap):
    tanda = "OK  " if dapat == harap else "GAGAL"
    print(f"{tanda} {nama}: {dapat:,} (harap {harap:,})")
    return dapat == harap


def main():
    f = faktur_contoh()
    h = ins.hitung(f, 8, 2026, pct_teknisi=30, pct_pool=2.0,
                   porsi={"sales": 50, "admin": 30, "store_leader": 20})
    lulus = [
        # 300rb + 100rb, sparepart tidak ikut
        cek("omset jasa", h["omset_jasa"], 400_000),
        cek("omset jasa member", h["omset_jasa_member"], 300_000),
        cek("sparepart faktur service", h["omset_sparepart_service"], 50_000),
        cek("bagi hasil MFlash 70%", h["bagi_hasil_mflash"], 280_000),
        cek("pool 2%", h["pool"], 5_600),
        cek("bagian sales 50%", h["bagian"]["sales"], 2_800),
        cek("bagian admin 30%", h["bagian"]["admin"], 1_680),
        cek("bagian store leader 20%", h["bagian"]["store_leader"], 1_120),
        # Andi menyerahkan dua-duanya -> seluruh jatah sales
        cek("Andi (sales) dapat semua", h["sales"][0]["insentif"], 2_800),
        # Budi 300rb dari 400rb -> 75% dari 1.680
        cek("Budi (admin) 75%", h["admin"][0]["insentif"], 1_260),
        cek("Citra (admin) 25%", h["admin"][1]["insentif"], 420),
        # skema lama: 2% x (300rb x 70%)
        cek("skema lama", h["skema_lama"], 4_200),
    ]

    hanya_member = ins.hitung(f, 8, 2026, hanya_member=True, pct_pool=2.0)
    lulus.append(cek("basis member saja", hanya_member["omset_jasa"], 300_000))

    kosong = ins.hitung(f, 7, 2026)
    lulus.append(cek("bulan tanpa data", kosong["omset_jasa"], 0))

    print()
    print("SEMUA UJI LULUS" if all(lulus) else "ADA UJI YANG GAGAL")
    return 0 if all(lulus) else 1


if __name__ == "__main__":
    raise SystemExit(main())
