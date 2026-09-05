"""Simulasi Insentif Service MFlash — Front Liner & Store Leader.

Aturan baru: setiap omset jasa service menjadi pencapaian Front Liner dan
Store Leader. Data dibaca dari berkas gabungan seluruh cabang di folder
`data/` pada repo ini.
"""
import io
import os

import altair as alt
import pandas as pd
import streamlit as st

import insentif as ins

st.set_page_config(page_title="Simulasi Insentif Service MFlash",
                   page_icon="🔧", layout="wide")

NAVY, ORANYE, ABU = "#14355B", "#F58F22", "#7A8CA3"
PERAN = ["Front Liner", "Store Leader"]
WARNA = alt.Scale(domain=PERAN, range=[NAVY, ORANYE])

st.markdown("""
<style>
  .stMetric {background:#fff;border:1px solid #E4D9C6;border-radius:10px;
             padding:12px 14px}
  div[data-testid="stMetricValue"] {font-size:1.45rem; white-space:nowrap}
  div[data-testid="stMetricLabel"] p {font-size:0.82rem}
  h1,h2,h3 {color:#14355B}
  section[data-testid="stSidebar"] {background:#EFE4D2}
</style>""", unsafe_allow_html=True)

BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def rupiah(n) -> str:
    return "Rp " + f"{float(n or 0):,.0f}".replace(",", ".")


def ribuan(n) -> str:
    return f"{int(n):,}".replace(",", ".")


@st.cache_data(show_spinner="Memuat data gabungan…")
def muat_repo(folder: str = "data"):
    return ins.muat_folder(folder)


@st.cache_data(show_spinner="Membaca berkas…")
def muat_unggahan(isi: bytes, nama: str):
    return ins.siapkan(ins.baca_berkas(io.BytesIO(isi), nama))


# ----------------------------------------------------------------- data
st.title("Simulasi Insentif Service")
st.caption("Setiap omset jasa service menjadi pencapaian **Front Liner** dan "
           "**Store Leader**. Geser parameter di kiri untuk mencoba skenario, "
           "lalu bandingkan biayanya dengan skema lama.")

with st.sidebar:
    st.header("1. Data")
    ada_repo = os.path.isdir("data") and any(
        f.endswith((".csv.gz", ".csv")) for f in os.listdir("data"))
    pilihan = ["Database repo (data/*.csv.gz)", "Unggah berkas"]
    sumber = st.radio("Sumber", pilihan, index=0 if ada_repo else 1,
                      label_visibility="collapsed")

df = None
if sumber.startswith("Database"):
    try:
        df = muat_repo()
        with st.sidebar:
            st.success(f"{ribuan(len(df))} baris · "
                       f"{len(ins.daftar_cabang(df))} cabang")
    except Exception as e:  # noqa: BLE001
        st.error(f"Database repo belum bisa dibaca: {e}")
        st.info("Buat berkasnya dengan `python gabung.py <folder-ekspor>` "
                "lalu commit `data/faktur-gabungan.csv.gz` ke GitHub, atau "
                "pilih **Unggah berkas** di panel kiri.")
        st.stop()
else:
    with st.sidebar:
        naik = st.file_uploader("Faktur (.csv.gz / .csv / .xlsx)",
                                type=["gz", "csv", "xlsx", "xlsm"])
    if not naik:
        st.info("Unggah berkas faktur di panel kiri, atau pilih "
                "**Database repo** bila datanya sudah ada di repo.")
        st.stop()
    try:
        df = muat_unggahan(naik.getvalue(), naik.name)
    except Exception as e:  # noqa: BLE001
        st.error(f"Berkas tidak bisa dibaca: {e}")
        st.stop()

periode = ins.periode_tersedia(df)
semua_cabang = ins.daftar_cabang(df)
if not periode:
    st.error("Tidak ada tanggal faktur yang terbaca.")
    st.stop()

# ----------------------------------------------------------------- parameter
with st.sidebar:
    st.header("2. Cakupan")
    tahun, bulan = st.selectbox(
        "Periode", periode,
        format_func=lambda p: f"{BULAN[p[1]]} {p[0]}")
    cabang = st.multiselect("Cabang", semua_cabang, default=semua_cabang,
                            help="Kosongkan untuk memilih semua cabang.")
    cabang = cabang or semua_cabang

    st.header("3. Dasar perhitungan")
    pct_teknisi = st.slider("Bagi hasil teknisi (%)", 0.0, 60.0, 30.0, 1.0,
                            help="Sisanya menjadi bagian MFlash dan itulah "
                                 "dasar pool insentif.")
    basis = st.radio("Pelanggan yang dihitung",
                     ["Semua pelanggan", "Member Reguler saja"], index=0,
                     help="Skema lama hanya menghitung Member Reguler.")
    pct_pool = st.slider("Pool insentif (% dari bagi hasil MFlash)",
                         0.0, 6.0, 2.0, 0.05)

    st.header("4. Proporsi")
    p_fl = st.slider("Front Liner (%)", 0, 100, 80, 5)
    p_sl = 100 - p_fl
    st.caption(f"Store Leader otomatis **{p_sl}%**.")
    bobot = st.slider("Dalam Front Liner: bobot yang menyerahkan unit (%)",
                      0, 100, 60, 5,
                      help="Sisanya untuk yang mengurus faktur. Bila salah "
                           "satu nama kosong, seluruh bobot jatuh ke yang ada.")

hasil = ins.hitung(
    df, bulan, tahun, cabang=cabang,
    pct_teknisi=pct_teknisi,
    hanya_member=(basis == "Member Reguler saja"),
    pct_pool=pct_pool,
    porsi_front_liner=p_fl, porsi_store_leader=p_sl,
    bobot_penyerah=bobot,
)

if hasil["omset_jasa"] == 0:
    st.warning("Tidak ada omset jasa service pada periode dan cabang ini.")
    st.stop()

# ----------------------------------------------------------------- ringkasan
k1, k2, k3, k4 = st.columns(4)
k1.metric("Omset jasa service", rupiah(hasil["omset_jasa"]),
          f"{ribuan(hasil['jumlah_faktur_service'])} faktur service")
k2.metric(f"Bagi hasil MFlash ({100 - pct_teknisi:.0f}%)",
          rupiah(hasil["bagi_hasil_mflash"]))
k3.metric(f"Pool insentif ({pct_pool:.2f}%)", rupiah(hasil["pool"]))
k4.metric("Selisih vs skema lama", rupiah(hasil["selisih"]),
          f"skema lama {rupiah(hasil['skema_lama'])}", delta_color="inverse")

netral = ins.pct_netral_biaya(hasil)
if abs(hasil["selisih"]) > 1000:
    arah = "lebih mahal" if hasil["selisih"] > 0 else "lebih murah"
    lingkup = ("seluruh cabang terpilih" if len(hasil["cabang"]) > 1
               else hasil["cabang"][0] if hasil["cabang"] else "cabang ini")
    st.info(f"Skema ini **{arah} {rupiah(abs(hasil['selisih']))}** pada "
            f"{BULAN[bulan]} {tahun} untuk {lingkup}, dibanding Insentif Team "
            f"2% yang berlaku sekarang. Agar biayanya sama persis, pakai pool "
            f"**{netral}%**.")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Ringkasan", "Rincian per orang", "Perbandingan skenario", "Catatan data"])

# ----------------------------------------------------------------- tab 1
with tab1:
    kiri, kanan = st.columns([1, 1.3])
    total_porsi = (p_fl + p_sl) or 1
    ringkas = pd.DataFrame([
        {"Peran": "Front Liner", "Porsi": f"{p_fl / total_porsi * 100:.0f}%",
         "Nominal": hasil["bagian"]["front_liner"],
         "Orang": len(hasil["front_liner"])},
        {"Peran": "Store Leader", "Porsi": f"{p_sl / total_porsi * 100:.0f}%",
         "Nominal": hasil["bagian"]["store_leader"],
         "Orang": len(hasil["store_leader"])},
    ])

    with kiri:
        st.subheader("Pembagian pool")
        tampil = ringkas.copy()
        tampil["Nominal"] = tampil["Nominal"].map(rupiah)
        st.dataframe(tampil, hide_index=True, use_container_width=True)
        st.metric("Total pool", rupiah(hasil["pool"]))
        if len(hasil["cabang"]) > 1:
            st.caption(f"Bagian Store Leader dibagi rata ke "
                       f"{len(hasil['cabang'])} cabang: "
                       f"{rupiah(hasil['store_leader'][0]['insentif'])} "
                       f"per cabang.")

    with kanan:
        st.subheader("Nominal per peran")
        st.altair_chart(
            alt.Chart(ringkas).mark_bar(cornerRadiusEnd=4).encode(
                x=alt.X("Nominal:Q", title="Rupiah",
                        axis=alt.Axis(format="~s")),
                y=alt.Y("Peran:N", sort="-x", title=None),
                color=alt.Color("Peran:N", legend=None, scale=WARNA),
                tooltip=["Peran:N", alt.Tooltip("Nominal:Q", format=",.0f")],
            ).properties(height=170), use_container_width=True)

    st.subheader("Sepuluh penerima terbesar")
    banyak_cabang = len(hasil["cabang"]) > 1
    gabung = ([{"Nama": (f"{r['nama']} · {r['cabang']}" if banyak_cabang
                         else r["nama"]),
                "Peran": "Front Liner",
                "Insentif": r["insentif"]} for r in hasil["front_liner"]]
              + [{"Nama": f"{r['nama']} · {r['cabang']}",
                  "Peran": "Store Leader", "Insentif": r["insentif"]}
                 for r in hasil["store_leader"]])
    df_g = pd.DataFrame(gabung).sort_values("Insentif", ascending=False).head(10)
    st.altair_chart(
        alt.Chart(df_g).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X("Insentif:Q", title="Rupiah", axis=alt.Axis(format="~s")),
            y=alt.Y("Nama:N", sort="-x", title=None),
            color=alt.Color("Peran:N", scale=WARNA),
            tooltip=["Nama", "Peran", alt.Tooltip("Insentif:Q", format=",.0f")],
        ).properties(height=max(240, 32 * len(df_g))), use_container_width=True)

# ----------------------------------------------------------------- tab 2
with tab2:
    st.subheader("Front Liner")
    st.caption(f"Tiap baris jasa memberi kredit ke dua orang: yang "
               f"menyerahkan unit **{bobot}%** dan yang mengurus faktur "
               f"**{100 - bobot}%**. Jatah peran "
               f"{rupiah(hasil['bagian']['front_liner'])} dibagi pro-rata "
               f"menurut kredit itu.")
    df_fl = pd.DataFrame(hasil["front_liner"]).rename(columns={
        "nama": "Nama", "cabang": "Cabang", "sebagai": "Berperan sebagai",
        "kredit_omset": "Kredit Omset", "andil_pct": "Andil (%)",
        "insentif": "Insentif"})
    if not df_fl.empty:
        tot = pd.DataFrame([{"Nama": "TOTAL", "Cabang": "",
                             "Berperan sebagai": "",
                             "Kredit Omset": df_fl["Kredit Omset"].sum(),
                             "Andil (%)": 100.0,
                             "Insentif": df_fl["Insentif"].sum()}])
        lihat = pd.concat([df_fl, tot], ignore_index=True)
        lihat["Kredit Omset"] = lihat["Kredit Omset"].map(rupiah)
        lihat["Insentif"] = lihat["Insentif"].map(rupiah)
        st.dataframe(lihat, hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Store Leader")
    df_sl = pd.DataFrame(hasil["store_leader"]).rename(columns={
        "cabang": "Cabang", "nama": "Nama", "omset_jasa": "Omset Jasa Cabang",
        "insentif": "Insentif"})
    lihat_sl = df_sl.copy()
    lihat_sl["Omset Jasa Cabang"] = lihat_sl["Omset Jasa Cabang"].map(rupiah)
    lihat_sl["Insentif"] = lihat_sl["Insentif"].map(rupiah)
    st.dataframe(lihat_sl, hide_index=True, use_container_width=True)
    st.caption("Nama Store Leader tidak ada di data faktur. Isi kolom `cabang` "
               "pada berkas gabungan sudah cukup untuk simulasi; nama "
               "sebenarnya bisa ditambahkan belakangan lewat master cabang.")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as tulis:
        pd.DataFrame([
            {"Uraian": "Periode", "Nilai": f"{BULAN[bulan]} {tahun}"},
            {"Uraian": "Cabang", "Nilai": ", ".join(hasil["cabang"])},
            {"Uraian": "Omset jasa service", "Nilai": hasil["omset_jasa"]},
            {"Uraian": f"Bagi hasil MFlash ({100 - pct_teknisi:.0f}%)",
             "Nilai": hasil["bagi_hasil_mflash"]},
            {"Uraian": f"Pool insentif ({pct_pool}%)", "Nilai": hasil["pool"]},
            {"Uraian": f"Bagian Front Liner ({p_fl}%)",
             "Nilai": hasil["bagian"]["front_liner"]},
            {"Uraian": f"Bagian Store Leader ({p_sl}%)",
             "Nilai": hasil["bagian"]["store_leader"]},
            {"Uraian": "Skema lama (Insentif Team)", "Nilai": hasil["skema_lama"]},
            {"Uraian": "Selisih", "Nilai": hasil["selisih"]},
        ]).to_excel(tulis, sheet_name="Ringkasan", index=False)
        if not df_fl.empty:
            df_fl.to_excel(tulis, sheet_name="Front Liner", index=False)
        df_sl.to_excel(tulis, sheet_name="Store Leader", index=False)
    st.download_button("Unduh hasil simulasi (.xlsx)", buf.getvalue(),
                       file_name=f"simulasi-insentif-service-{tahun}-"
                                 f"{bulan:02d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet")

# ----------------------------------------------------------------- tab 3
with tab3:
    st.subheader("Berapa biayanya pada berbagai tarif pool?")
    baris = []
    for p in sorted({0.5, 1.0, netral, 1.5, 2.0, 2.5, 3.0}):
        h = ins.hitung(df, bulan, tahun, cabang=cabang,
                       pct_teknisi=pct_teknisi,
                       hanya_member=(basis == "Member Reguler saja"),
                       pct_pool=p, porsi_front_liner=p_fl,
                       porsi_store_leader=p_sl, bobot_penyerah=bobot)
        baris.append({"tarif": p, "total": h["pool"],
                      "Front Liner": h["bagian"]["front_liner"],
                      "Store Leader": h["bagian"]["store_leader"],
                      "selisih": h["selisih"]})
    # Nama kolom sengaja tanpa tanda kurung atau persen: Altair memakai tanda
    # itu sebagai sintaks tersendiri dan grafiknya gagal dirender.
    df_s = pd.DataFrame(baris).sort_values("tarif")
    lihat = df_s.rename(columns={"tarif": "Tarif pool (%)", "total": "Total pool",
                                 "selisih": "Selisih vs lama"})
    for k in ("Total pool", "Front Liner", "Store Leader", "Selisih vs lama"):
        lihat[k] = lihat[k].map(rupiah)
    st.dataframe(lihat, hide_index=True, use_container_width=True)

    st.altair_chart(
        alt.Chart(df_s.melt(id_vars="tarif",
                            value_vars=["Front Liner", "Store Leader"],
                            var_name="Peran", value_name="Nominal")
                  ).mark_area(opacity=0.85).encode(
            x=alt.X("tarif:Q", title="Tarif pool (%)"),
            y=alt.Y("Nominal:Q", stack="zero", title="Rupiah",
                    axis=alt.Axis(format="~s")),
            color=alt.Color("Peran:N", scale=WARNA),
            tooltip=[alt.Tooltip("tarif:Q", title="Tarif pool (%)"), "Peran:N",
                     alt.Tooltip("Nominal:Q", format=",.0f")],
        ).properties(height=260), use_container_width=True)

    if len(semua_cabang) > 1:
        st.subheader("Perbandingan antar cabang")
        per_cab = []
        for c in semua_cabang:
            h = ins.hitung(df, bulan, tahun, cabang=[c],
                           pct_teknisi=pct_teknisi,
                           hanya_member=(basis == "Member Reguler saja"),
                           pct_pool=pct_pool, porsi_front_liner=p_fl,
                           porsi_store_leader=p_sl, bobot_penyerah=bobot)
            if h["omset_jasa"]:
                per_cab.append({"Cabang": c, "Omset jasa": h["omset_jasa"],
                                "Pool": h["pool"],
                                "Skema lama": h["skema_lama"],
                                "Selisih": h["selisih"],
                                "Front Liner": len(h["front_liner"])})
        if per_cab:
            dfc = pd.DataFrame(per_cab).sort_values("Omset jasa",
                                                    ascending=False)
            lihatc = dfc.copy()
            for k in ("Omset jasa", "Pool", "Skema lama", "Selisih"):
                lihatc[k] = lihatc[k].map(rupiah)
            st.dataframe(lihatc, hide_index=True, use_container_width=True)
            st.altair_chart(
                alt.Chart(dfc).mark_bar(cornerRadiusEnd=3, color=NAVY).encode(
                    x=alt.X("Pool:Q", title="Pool insentif",
                            axis=alt.Axis(format="~s")),
                    y=alt.Y("Cabang:N", sort="-x", title=None),
                    tooltip=["Cabang", alt.Tooltip("Pool:Q", format=",.0f"),
                             alt.Tooltip("Omset jasa:Q", format=",.0f")],
                ).properties(height=max(220, 26 * len(dfc))),
                use_container_width=True)

# ----------------------------------------------------------------- tab 4
with tab4:
    c1, c2, c3 = st.columns(3)
    c1.metric("Baris faktur diproses", ribuan(hasil["jumlah_baris"]))
    c2.metric("Sparepart pada faktur service",
              rupiah(hasil["omset_sparepart_service"]),
              help="Tidak masuk pool — hanya baris JASA yang dihitung.")
    c3.metric("Omset jasa tanpa nama sama sekali",
              rupiah(hasil["omset_tanpa_nama"]))

    if hasil["omset_tanpa_nama"]:
        st.warning(
            f"**{rupiah(hasil['omset_tanpa_nama'])}** omset jasa tidak punya "
            f"nama penyerah maupun nama admin. Nilainya tetap masuk pool "
            f"tetapi tidak bisa diatribusikan, sehingga menyebar ke nama lain. "
            f"Rapikan pengisiannya di sistem sumber agar adil.")

    mirip = ins.nama_mirip([r["nama"] for r in hasil["front_liner"]])
    if mirip:
        st.error("Nama berikut kemungkinan orang yang sama dengan dua ejaan, "
                 "sehingga insentifnya terpecah:\n\n"
                 + "\n".join(f"- **{a}** vs **{b}**" for a, b in mirip))

    st.markdown("""
**Yang perlu diputuskan sebelum aturan ini dipakai**

1. Pool ini **menggantikan** Insentif Team 2% yang lama, atau **ditambahkan**
   di atasnya? Simulasi ini menganggapnya mengganti.
2. Store Leader sudah menerima Insentif Profit. Kalau porsi di sini dianggap
   dobel, geser Front Liner ke 100%.
3. Perlukah ambang minimum, misalnya insentif baru dibayar bila omset jasa
   cabang melewati target bulanan?
4. Bobot 60 : 40 antara yang menyerahkan unit dan yang mengurus faktur — sudah
   sesuai beban kerja sebenarnya di cabang?
""")

st.caption("Simulasi — belum menjadi keputusan.")
