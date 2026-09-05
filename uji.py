"""Uji cepat mesin perhitungan tanpa berkas nyata.

Jalankan: python uji.py
"""
import pandas as pd

import insentif as ins


def contoh():
    """Dua faktur service pada satu cabang."""
    return pd.DataFrame([
        # F1: jasa 300rb, penyerah Andi, admin Budi
        ("2026-08-05", "F1", "Klender", "Member Reguler", "SERVICE HP",
         "JASA", 300_000, "Andi", "Budi", "Tono"),
        # sparepart pada faktur service: tidak masuk pool
        ("2026-08-05", "F1", "Klender", "Member Reguler", "SERVICE HP",
         "SPAREPART", 50_000, "Andi", "Budi", "Tono"),
        # F2: jasa 100rb, penyerah Andi, admin Citra, pelanggan umum
        ("2026-08-06", "F2", "Klender", "Umum", "SERVICE HP",
         "JASA", 100_000, "Andi", "Citra", "Tono"),
        # F3: cabang lain, admin kosong -> seluruh bobot ke penyerah
        ("2026-08-07", "F3", "Bintara", "Member Reguler", "SERVICE LAPTOP",
         "JASA", 200_000, "Dina", "", "Tono"),
    ], columns=["tanggal", "no_faktur", "cabang", "kategori_pelanggan",
                "kategori_penjualan", "kategori_barang", "total_harga",
                "penyerah", "admin", "teknisi"])


def cek(nama, dapat, harap):
    tanda = "OK  " if dapat == harap else "GAGAL"
    print(f"{tanda} {nama}: {dapat:,} (harap {harap:,})")
    return dapat == harap


def main():
    df = ins.siapkan(contoh())
    lulus = []

    # tanggal ISO tidak boleh terbaca tahun-HARI-bulan
    lulus.append(cek("semua faktur di bulan 8", int((df["bulan"] == 8).sum()), 4))

    h = ins.hitung(df, 8, 2026, cabang=["Klender"], pct_teknisi=30,
                   pct_pool=2.0, porsi_front_liner=80, porsi_store_leader=20,
                   bobot_penyerah=60)
    lulus += [
        cek("omset jasa Klender", h["omset_jasa"], 400_000),
        cek("sparepart tidak ikut", h["omset_sparepart_service"], 50_000),
        cek("bagi hasil MFlash 70%", h["bagi_hasil_mflash"], 280_000),
        cek("pool 2%", h["pool"], 5_600),
        cek("bagian front liner 80%", h["bagian"]["front_liner"], 4_480),
        cek("bagian store leader 20%", h["bagian"]["store_leader"], 1_120),
    ]
    # kredit: Andi 60% x 400rb = 240rb; Budi 40% x 300rb = 120rb;
    #         Citra 40% x 100rb = 40rb. Total 400rb = omset jasa.
    kredit = {r["nama"]: r["kredit_omset"] for r in h["front_liner"]}
    lulus += [
        cek("kredit Andi", kredit["Andi"], 240_000),
        cek("kredit Budi", kredit["Budi"], 120_000),
        cek("kredit Citra", kredit["Citra"], 40_000),
        cek("jumlah kredit = omset jasa", sum(kredit.values()), 400_000),
    ]
    ins_fl = {r["nama"]: r["insentif"] for r in h["front_liner"]}
    lulus += [
        cek("insentif Andi 60%", ins_fl["Andi"], 2_688),
        cek("insentif Budi 30%", ins_fl["Budi"], 1_344),
        cek("insentif Citra 10%", ins_fl["Citra"], 448),
        cek("skema lama 2% x (300rb x 70%)", h["skema_lama"], 4_200),
    ]

    # admin kosong: seluruh bobot ke penyerah
    hb = ins.hitung(df, 8, 2026, cabang=["Bintara"], pct_pool=2.0)
    kb = {r["nama"]: r["kredit_omset"] for r in hb["front_liner"]}
    lulus.append(cek("Dina dapat kredit penuh", kb["Dina"], 200_000))

    # dua cabang: bagian store leader dibagi rata
    h2 = ins.hitung(df, 8, 2026, pct_pool=2.0, porsi_front_liner=80,
                    porsi_store_leader=20)
    lulus += [
        cek("omset dua cabang", h2["omset_jasa"], 600_000),
        cek("jumlah cabang", len(h2["store_leader"]), 2),
        cek("store leader per cabang",
            h2["store_leader"][0]["insentif"], 840),
    ]

    hm = ins.hitung(df, 8, 2026, cabang=["Klender"], hanya_member=True)
    lulus.append(cek("basis member saja", hm["omset_jasa"], 300_000))
    lulus.append(cek("bulan tanpa data", ins.hitung(df, 7, 2026)["omset_jasa"], 0))

    print()
    print("SEMUA UJI LULUS" if all(lulus) else "ADA UJI YANG GAGAL")
    return 0 if all(lulus) else 1


if __name__ == "__main__":
    raise SystemExit(main())
