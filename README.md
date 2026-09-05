# Simulasi Insentif Service — MFlash

Aplikasi Streamlit untuk mencoba **aturan baru Insentif Sales & Team**: setiap
omset jasa service menjadi pencapaian **Front Liner** dan **Store Leader**.

Aplikasi ini **simulasi**, bukan aplikasi pengajuan. Tujuannya menjawab satu
pertanyaan sebelum aturan diputuskan: *kalau proporsinya sekian, siapa dapat
berapa, dan biayanya naik berapa?*

---

## Skema yang disimulasikan

```
Omset jasa service (baris KATEGORI BARANG = JASA)
        │
        ├─ bagian teknisi        30%   (bisa diubah)
        └─ bagi hasil MFlash     70%
                 │
                 └─ Pool insentif = 2% dari bagi hasil MFlash
                          │
                          ├─ Front Liner   80%
                          │      tiap baris jasa memberi kredit ke dua orang:
                          │      yang menyerahkan unit 60%, yang mengurus faktur 40%
                          │      lalu dibagi pro-rata menurut kredit
                          │
                          └─ Store Leader  20%  → dibagi rata antar cabang
```

Semua angka di atas hanya nilai awal — semuanya bisa digeser di panel kiri.

**Front Liner** menggabungkan dua kolom pada faktur: `YANG
MENYERAHKAN/MENJUAL` dan `NAMA ADMIN`. Satu orang yang mengisi kedua peran
pada faktur berbeda tetap dihitung sebagai satu orang, dan kolom *Berperan
sebagai* menunjukkan perannya.

**Kenapa dibagi berbobot, bukan dijumlahkan begitu saja?** Supaya total kredit
selalu sama dengan total omset jasa. Kalau satu baris dihitung penuh untuk
kedua nama, kredit menjadi dua kali omset dan persentase andilnya kehilangan
makna.

**Kenapa pro-rata, bukan dibagi rata?** Karena orang yang menangani omset jasa
Rp 67 juta dan yang menangani Rp 1,9 juta tidak pantas menerima sama besar.

Nama dikelompokkan per **(cabang, nama)** — orang bernama sama di dua cabang
adalah dua orang berbeda.

---

## Database: satu berkas csv.gz untuk semua cabang

Data tinggal di folder `data/` pada repo ini, jadi aplikasi langsung hidup
tanpa siapa pun perlu mengunggah apa-apa.

### Membuat berkas gabungan

Kumpulkan ekspor **Rincian Faktur Penjualan** tiap cabang dalam satu folder,
beri nama berkas sesuai cabangnya (`klender.xlsx`, `bintara.xlsx`, …), lalu:

```bash
python gabung.py folder-ekspor
```

Hasilnya `data/faktur-gabungan.csv.gz`. Skrip akan:

- membaca `.xlsx`, `.csv`, maupun `.csv.gz`;
- membakukan nama kolom yang berbeda-beda antar versi ekspor;
- mengambil nama cabang dari kolom `CABANG` bila ada, kalau tidak dari nama
  berkas;
- memperingatkan bila satu cabang-periode muncul di lebih dari satu berkas
  (tanda berkas terunggah dua kali).

Baris kembar **tidak** dibuang: satu faktur wajar memuat dua baris identik
(mis. dua sparepart sama harga), dan membuangnya mengurangi omset yang sah.

### Kolom pada berkas gabungan

`tanggal, no_faktur, cabang, kategori_pelanggan, kategori_penjualan,
kategori_barang, total_harga, penyerah, admin, teknisi`

Nama pelanggan dan ID pelanggan **tidak ikut** disimpan — tidak diperlukan
untuk perhitungan, dan repo jadi lebih aman.

### Menambah bulan baru

Jalankan `gabung.py` lagi dengan seluruh ekspor (lama + baru), lalu commit
berkasnya. Atau simpan per periode: `data/2026-08.csv.gz`,
`data/2026-09.csv.gz` — semua berkas `.csv.gz` di folder `data/` otomatis
digabung saat aplikasi dijalankan.

Ukuran: 1.886 baris jadi sekitar 40 KB terkompresi, jadi setahun penuh 18
cabang pun masih jauh di bawah batas 100 MB per berkas di GitHub.

---

## Menjalankan di komputer sendiri

```bash
pip install -r requirements.txt
python gabung.py folder-ekspor      # sekali, untuk menyiapkan data
streamlit run app.py
```

Buka `http://localhost:8501`.

> Kalau Anda mengubah `insentif.py` saat Streamlit berjalan, hentikan lalu
> jalankan ulang. Streamlit memuat ulang `app.py` secara otomatis tetapi
> tidak memuat ulang modul yang diimpornya.

---

## Menaruh di GitHub lalu online lewat Streamlit Cloud

### 1. Buat repo

Buka <https://github.com/new>, beri nama misalnya
`simulasi-insentif-service`, pilih **Private**, lalu **Create repository**.
Jangan centang "Add a README" — sudah ada di sini.

### 2. Unggah kode dan data

```bash
git remote add origin https://github.com/<akun-anda>/simulasi-insentif-service.git
git add -A && git commit -m "Data gabungan seluruh cabang"
git push -u origin main
```

Kalau GitHub meminta password, yang dipakai bukan password akun melainkan
**Personal Access Token**: Settings → Developer settings → Personal access
tokens → Tokens (classic) → Generate new token, centang `repo`.

Tidak terbiasa dengan git? Buka repo di GitHub, klik **Add file → Upload
files**, seret semua berkas dari folder ini (termasuk folder `data/`), lalu
**Commit changes**.

### 3. Deploy ke Streamlit Community Cloud (gratis)

1. Buka <https://share.streamlit.io> dan masuk dengan akun GitHub.
2. **Create app** → pilih repo Anda.
3. Branch `main`, Main file path `app.py`.
4. **Deploy**. Sekitar dua menit, aplikasi hidup di
   `https://<nama>.streamlit.app`.

Setiap `git push` membuat Streamlit Cloud memperbarui aplikasinya sendiri —
termasuk ketika yang Anda push hanya data bulan baru.

> `.gitignore` menghalangi `*.xlsx` ikut ter-commit supaya ekspor mentah
> berisi data pelanggan tidak pernah naik ke GitHub. Berkas `data/*.csv.gz`
> sengaja dikecualikan dari larangan itu karena memang itulah databasenya.
> Kalau repo dibuat publik, ingat bahwa nama karyawan ikut terbaca siapa pun.

---

## Isi repo

| Berkas | Isi |
|---|---|
| `app.py` | tampilan Streamlit |
| `insentif.py` | mesin perhitungan, terpisah supaya mudah diuji |
| `gabung.py` | menggabungkan ekspor per cabang menjadi `data/*.csv.gz` |
| `uji.py` | 21 uji angka (`python uji.py`) |
| `data/` | database gabungan seluruh cabang |
| `requirements.txt` | daftar pustaka |
| `.streamlit/config.toml` | warna MFlash |

---

## Batas yang perlu diketahui

- Omset jasa yang **kedua** kolom namanya kosong tetap masuk pool tetapi tidak
  bisa diatribusikan; nilainya ditampilkan di tab **Catatan data**.
- Nama dengan dua ejaan (mis. `ARIF FIKRI` dan `ARIF FIKRI KLENDER`) dihitung
  sebagai dua orang. Aplikasi menandainya; perbaikannya di sistem sumber.
- Sparepart pada faktur service **tidak** masuk pool — hanya baris `JASA`.
- Nama Store Leader tidak ada di data faktur, jadi yang tampil nama cabangnya.
