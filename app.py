"""Simulasi Insentif Service MFlash — Sales, Admin, Store Leader.

Aturan baru: setiap omset jasa service ikut menjadi pencapaian tiga peran
sekaligus. Aplikasi ini dipakai untuk mencoba angkanya sebelum diputuskan.
"""
import io

import altair as alt
import pandas as pd
import streamlit as st

import insentif as ins

st.set_page_config(page_title="Simulasi Insentif Service MFlash",
                   page_icon="🔧", layout="wide")

NAVY, ORANYE = "#14355B", "#F58F22"

st.markdown("""
<style>
  .stMetric {background:#fff;border:1px solid #E4D9C6;border-radius:10px;
             padding:12px 14px}
  div[data-testid="stMetricValue"] {font-size:1.45rem; white-space:nowrap}
  div[data-testid="stMetricLabel"] p {font-size:0.82rem}
  h1,h2,h3 {color:#14355B}
  section[data-testid="stSidebar"] {background:#EFE4D2}
</style>""", unsafe_allow_html=True)


def rupiah(n) -> str:
    return "Rp " + f"{float(n or 0):,.0f}".replace(",", ".")


# ----------------------------------------------------------------- masukan
st.title("Simulasi Insentif Service")
st.caption("Setiap omset jasa service menjadi pencapaian Sales, Admin, dan "
           "Store Leader sekaligus. Geser parameter di kiri untuk mencoba "
           "skenario, lalu bandingkan biayanya dengan skema lama.")

with st.sidebar:
    st.header("1. Data")
    berkas = st.file_uploader("Rincian Faktur Penjualan (.xlsx)",
                              type=["xlsx", "xlsm"])
    st.caption("Ekspor apa adanya dari sistem. Berkas tidak disimpan di mana pun.")

if not berkas:
    st.info("Unggah berkas **Rincian Faktur Penjualan** di panel kiri untuk mulai.")
    with st.expander("Kolom apa saja yang dipakai?"):
        st.markdown("""
| Kolom | Dipakai untuk |
|---|---|
| `TGL FAKTUR` | menyaring periode |
| `KATEGORI BARANG` | mengambil baris **JASA** sebagai omset service |
| `KATEGORI PENJUALAN` | menandai faktur service |
| `KATEGORI PELANGGAN` | opsi basis Member Reguler |
| `TOTAL HARGA` | nilai omset |
| `YANG MENYERAHKAN/MENJUAL` | pembagian porsi **Sales** |
| `NAMA ADMIN` | pembagian porsi **Admin** |
""")
    st.stop()

try:
    faktur = ins.baca_faktur(berkas)
except Exception as e:  # noqa: BLE001
    st.error(f"Berkas tidak bisa dibaca: {e}")
    st.stop()

periode = ins.periode_tersedia(faktur)
if not periode:
    st.error("Tidak ada tanggal faktur yang terbaca di berkas ini.")
    st.stop()

BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]

with st.sidebar:
    pilih = st.selectbox("Periode", periode,
                         format_func=lambda p: f"{BULAN[p[1]]} {p[0] or ''}".strip())
    tahun, bulan = pilih

    st.header("2. Dasar perhitungan")
    pct_teknisi = st.slider("Bagi hasil teknisi (%)", 0.0, 60.0, 30.0, 1.0,
                            help="Sisanya menjadi bagian MFlash dan itulah "
                                 "dasar pool insentif.")
    basis = st.radio("Pelanggan yang dihitung",
                     ["Semua pelanggan", "Member Reguler saja"], index=0,
                     help="Skema lama hanya menghitung Member Reguler.")
    pct_pool = st.slider("Pool insentif (% dari bagi hasil MFlash)",
                         0.0, 6.0, 2.0, 0.05)

    st.header("3. Proporsi")
    st.caption("Boleh tidak berjumlah 100 — nilainya dinormalkan otomatis.")
    p_sales = st.slider("Sales", 0, 100, 50, 5)
    p_admin = st.slider("Admin", 0, 100, 30, 5)
    p_sl = st.slider("Store Leader", 0, 100, 20, 5)
    nama_sl = st.text_input("Nama Store Leader", "Store Leader")

hasil = ins.hitung(
    faktur, bulan, tahun,
    pct_teknisi=pct_teknisi,
    hanya_member=(basis == "Member Reguler saja"),
    pct_pool=pct_pool,
    porsi={"sales": p_sales, "admin": p_admin, "store_leader": p_sl},
    nama_store_leader=nama_sl or "Store Leader",
)

if hasil["omset_jasa"] == 0:
    st.warning("Tidak ada omset jasa service pada periode ini.")
    st.stop()

# ----------------------------------------------------------------- ringkasan
k1, k2, k3, k4 = st.columns(4)
k1.metric("Omset jasa service", rupiah(hasil["omset_jasa"]),
          f"{hasil['jumlah_faktur_service']:,} faktur service".replace(",", "."))
k2.metric(f"Bagi hasil MFlash ({100 - pct_teknisi:.0f}%)",
          rupiah(hasil["bagi_hasil_mflash"]))
k3.metric(f"Pool insentif ({pct_pool:.2f}%)", rupiah(hasil["pool"]))
k4.metric("Selisih vs skema lama", rupiah(hasil["selisih"]),
          f"skema lama {rupiah(hasil['skema_lama'])}",
          delta_color="inverse")

netral = ins.pct_netral_biaya(hasil)
if abs(hasil["selisih"]) > 1000:
    arah = "lebih mahal" if hasil["selisih"] > 0 else "lebih murah"
    st.info(f"Skema ini **{arah} {rupiah(abs(hasil['selisih']))}** per bulan "
            f"per cabang dibanding Insentif Team 2% yang berlaku sekarang. "
            f"Agar biayanya sama persis, pakai pool **{netral}%**.")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Ringkasan", "Rincian per orang", "Perbandingan skenario", "Catatan data"])

# ----------------------------------------------------------------- tab 1
with tab1:
    kiri, kanan = st.columns([1, 1.3])

    with kiri:
        st.subheader("Pembagian pool")
        total_porsi = (p_sales + p_admin + p_sl) or 1
        ringkas = pd.DataFrame([
            {"Peran": "Sales", "Porsi": f"{p_sales / total_porsi * 100:.0f}%",
             "Nominal": hasil["bagian"]["sales"], "Orang": len(hasil["sales"])},
            {"Peran": "Admin", "Porsi": f"{p_admin / total_porsi * 100:.0f}%",
             "Nominal": hasil["bagian"]["admin"], "Orang": len(hasil["admin"])},
            {"Peran": "Store Leader", "Porsi": f"{p_sl / total_porsi * 100:.0f}%",
             "Nominal": hasil["bagian"]["store_leader"], "Orang": 1},
        ])
        tampil = ringkas.copy()
        tampil["Nominal"] = tampil["Nominal"].map(rupiah)
        st.dataframe(tampil, hide_index=True, use_container_width=True)
        st.metric("Total pool", rupiah(hasil["pool"]))

    with kanan:
        st.subheader("Nominal per peran")
        st.altair_chart(
            alt.Chart(ringkas).mark_bar(cornerRadiusEnd=4).encode(
                x=alt.X("Nominal:Q", title="Rupiah",
                        axis=alt.Axis(format="~s")),
                y=alt.Y("Peran:N", sort="-x", title=None),
                color=alt.Color("Peran:N", legend=None,
                                scale=alt.Scale(domain=["Sales", "Admin",
                                                        "Store Leader"],
                                                range=[NAVY, ORANYE,
                                                       "#7A8CA3"])),
                tooltip=[alt.Tooltip("Peran:N"),
                         alt.Tooltip("Nominal:Q", format=",.0f")],
            ).properties(height=210), use_container_width=True)

    st.subheader("Sepuluh penerima terbesar")
    st.caption("Batang bertumpuk: bagian gelap dari peran Sales, bagian oranye dari peran Admin.")
    gabung = ([{"Nama": r["nama"], "Peran": "Sales", "Insentif": r["insentif"]}
               for r in hasil["sales"]]
              + [{"Nama": r["nama"], "Peran": "Admin", "Insentif": r["insentif"]}
                 for r in hasil["admin"]]
              + [{"Nama": hasil["store_leader"]["nama"], "Peran": "Store Leader",
                  "Insentif": hasil["store_leader"]["insentif"]}])
    df_all = pd.DataFrame(gabung)
    # Satu orang bisa berperan ganda; peringkat diambil dari totalnya lalu
    # batangnya tetap dipecah per peran.
    urut = (df_all.groupby("Nama")["Insentif"].sum()
            .sort_values(ascending=False).head(10).index.tolist())
    df_g = df_all[df_all["Nama"].isin(urut)]
    st.altair_chart(
        alt.Chart(df_g).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X("Insentif:Q", title="Rupiah", axis=alt.Axis(format="~s")),
            y=alt.Y("Nama:N", sort=urut, title=None),
            color=alt.Color("Peran:N",
                            scale=alt.Scale(domain=["Sales", "Admin",
                                                    "Store Leader"],
                                            range=[NAVY, ORANYE, "#7A8CA3"])),
            tooltip=["Nama", "Peran", alt.Tooltip("Insentif:Q", format=",.0f")],
        ).properties(height=max(260, 34 * len(urut))), use_container_width=True)

    st.caption("Satu orang bisa muncul dua kali bila ia menjadi Sales pada "
               "sebagian faktur dan Admin pada faktur lain — memang begitu "
               "maksud aturan barunya.")

# ----------------------------------------------------------------- tab 2
with tab2:
    def tabel(baris, jatah, judul):
        st.subheader(judul)
        if not baris:
            st.caption("Tidak ada data.")
            return pd.DataFrame()
        df = pd.DataFrame(baris).rename(columns={
            "nama": "Nama", "omset_jasa": "Omset Jasa",
            "andil_pct": "Andil (%)", "insentif": "Insentif"})
        tot = pd.DataFrame([{"Nama": "TOTAL",
                             "Omset Jasa": df["Omset Jasa"].sum(),
                             "Andil (%)": 100.0,
                             "Insentif": df["Insentif"].sum()}])
        lihat = pd.concat([df, tot], ignore_index=True)
        lihat["Omset Jasa"] = lihat["Omset Jasa"].map(rupiah)
        lihat["Insentif"] = lihat["Insentif"].map(rupiah)
        st.dataframe(lihat, hide_index=True, use_container_width=True)
        st.caption(f"Jatah peran ini {rupiah(jatah)}, dibagi pro-rata menurut "
                   f"andil omset jasa masing-masing.")
        return df

    df_sales = tabel(hasil["sales"], hasil["bagian"]["sales"],
                     "Sales — dasar kolom “Yang Menyerahkan/Menjual”")
    st.divider()
    df_admin = tabel(hasil["admin"], hasil["bagian"]["admin"],
                     "Admin — dasar kolom “Nama Admin”")
    st.divider()
    st.subheader("Store Leader")
    st.dataframe(pd.DataFrame([{
        "Nama": hasil["store_leader"]["nama"],
        "Dasar": "Seluruh omset jasa cabang",
        "Insentif": rupiah(hasil["store_leader"]["insentif"])}]),
        hide_index=True, use_container_width=True)
    st.caption("Store Leader menerima utuh tanpa dibagi, karena "
               "pertanggungjawabannya atas seluruh cabang.")

    # ---- unduh
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as tulis:
        pd.DataFrame([
            {"Uraian": "Periode",
             "Nilai": f"{BULAN[bulan]} {tahun or ''}".strip()},
            {"Uraian": "Omset jasa service", "Nilai": hasil["omset_jasa"]},
            {"Uraian": f"Bagi hasil MFlash ({100 - pct_teknisi:.0f}%)",
             "Nilai": hasil["bagi_hasil_mflash"]},
            {"Uraian": f"Pool insentif ({pct_pool}%)", "Nilai": hasil["pool"]},
            {"Uraian": "Bagian Sales", "Nilai": hasil["bagian"]["sales"]},
            {"Uraian": "Bagian Admin", "Nilai": hasil["bagian"]["admin"]},
            {"Uraian": "Bagian Store Leader",
             "Nilai": hasil["bagian"]["store_leader"]},
            {"Uraian": "Skema lama (Insentif Team)", "Nilai": hasil["skema_lama"]},
            {"Uraian": "Selisih", "Nilai": hasil["selisih"]},
        ]).to_excel(tulis, sheet_name="Ringkasan", index=False)
        if not df_sales.empty:
            df_sales.to_excel(tulis, sheet_name="Sales", index=False)
        if not df_admin.empty:
            df_admin.to_excel(tulis, sheet_name="Admin", index=False)
    st.download_button("Unduh hasil simulasi (.xlsx)", buf.getvalue(),
                       file_name=f"simulasi-insentif-service-"
                                 f"{tahun}-{bulan:02d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet")

# ----------------------------------------------------------------- tab 3
with tab3:
    st.subheader("Berapa biayanya pada berbagai tarif pool?")
    st.caption("Semua angka memakai dasar dan proporsi yang sedang dipilih.")
    baris = []
    for p in [0.5, 1.0, netral, 1.5, 2.0, 2.5, 3.0]:
        h = ins.hitung(faktur, bulan, tahun, pct_teknisi=pct_teknisi,
                       hanya_member=(basis == "Member Reguler saja"),
                       pct_pool=p,
                       porsi={"sales": p_sales, "admin": p_admin,
                              "store_leader": p_sl})
        baris.append({"tarif": p, "total": h["pool"],
                      "Sales": h["bagian"]["sales"],
                      "Admin": h["bagian"]["admin"],
                      "Store Leader": h["bagian"]["store_leader"],
                      "selisih": h["selisih"]})
    # Nama kolom sengaja tanpa tanda kurung atau persen: Altair memakai tanda
    # itu sebagai sintaks tersendiri dan grafiknya gagal dirender.
    df_s = pd.DataFrame(baris).drop_duplicates(
        subset="tarif").sort_values("tarif")
    lihat = df_s.rename(columns={"tarif": "Tarif pool (%)",
                                 "total": "Total pool",
                                 "selisih": "Selisih vs lama"})
    for k in ("Total pool", "Sales", "Admin", "Store Leader", "Selisih vs lama"):
        lihat[k] = lihat[k].map(rupiah)
    st.dataframe(lihat, hide_index=True, use_container_width=True)

    st.altair_chart(
        alt.Chart(df_s.melt(id_vars="tarif",
                            value_vars=["Sales", "Admin", "Store Leader"],
                            var_name="Peran", value_name="Nominal")
                  ).mark_area(opacity=0.85).encode(
            x=alt.X("tarif:Q", title="Tarif pool (%)"),
            y=alt.Y("Nominal:Q", stack="zero", title="Rupiah",
                    axis=alt.Axis(format="~s")),
            color=alt.Color("Peran:N",
                            scale=alt.Scale(domain=["Sales", "Admin",
                                                    "Store Leader"],
                                            range=[NAVY, ORANYE, "#7A8CA3"])),
            tooltip=[alt.Tooltip("tarif:Q", title="Tarif pool (%)"), "Peran:N",
                     alt.Tooltip("Nominal:Q", format=",.0f")],
        ).properties(height=280), use_container_width=True)

    st.markdown(f"""
**Pembacaan cepat**

- Tarif **{netral}%** membuat biaya persis sama dengan Insentif Team 2% yang
  berlaku sekarang — pilihan paling aman bila anggaran tidak boleh naik.
- Tarif **2%** adalah usulan saya: biayanya naik
  {rupiah(max(0, hasil['selisih']))} per cabang per bulan, tetapi tiga peran
  sekaligus ikut terdorong menaikkan omset service.
- Basis **Semua pelanggan** menaikkan pool sekitar 45% dibanding
  **Member Reguler saja**, karena sebagian besar omset jasa memang datang dari
  member.
""")

# ----------------------------------------------------------------- tab 4
with tab4:
    c1, c2 = st.columns(2)
    c1.metric("Baris faktur diproses",
              f"{hasil['jumlah_baris_diproses']:,}".replace(",", "."))
    c2.metric("Omset sparepart pada faktur service",
              rupiah(hasil["omset_sparepart_service"]),
              help="Tidak masuk perhitungan — pool hanya dari baris JASA.")

    if hasil["omset_tanpa_sales"] or hasil["omset_tanpa_admin"]:
        st.warning(
            f"Omset jasa tanpa nama penyerah: "
            f"**{rupiah(hasil['omset_tanpa_sales'])}** · tanpa nama admin: "
            f"**{rupiah(hasil['omset_tanpa_admin'])}**. Nilai ini tetap masuk "
            f"pool tetapi tidak bisa diatribusikan ke siapa pun, sehingga "
            f"pembagiannya menyebar ke nama lain. Rapikan pengisian kolomnya "
            f"di sistem agar adil.")

    mirip = ins.nama_mirip([r["nama"] for r in hasil["sales"]],
                           [r["nama"] for r in hasil["admin"]])
    if mirip:
        st.error("Nama berikut kemungkinan orang yang sama dengan dua ejaan, "
                 "sehingga insentifnya terpecah:\n\n"
                 + "\n".join(f"- **{a}** vs **{b}**" for a, b in mirip))

    st.markdown("""
**Yang perlu diputuskan sebelum aturan ini dipakai**

1. Apakah pool ini **menggantikan** Insentif Team 2% yang lama, atau
   **ditambahkan** di atasnya? Simulasi ini menganggapnya mengganti.
2. Apakah Store Leader yang sudah menerima Insentif Profit juga berhak atas
   porsi ini? Kalau dianggap dobel, porsinya bisa dinolkan dan dibagi ke
   Sales dan Admin.
3. Perlukah ambang minimum, misalnya insentif baru dibayar bila omset jasa
   cabang melewati target bulanan?
""")

st.caption("Simulasi — belum menjadi keputusan. Sumber angka: berkas yang "
           "Anda unggah, tidak disimpan di server.")
