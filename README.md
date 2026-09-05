# Simulasi Insentif Service — MFlash

Aplikasi Streamlit untuk mencoba **aturan baru Insentif Sales & Team**: setiap
omset jasa service menjadi pencapaian **Sales**, **Admin**, dan **Store Leader**
sekaligus.

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
                          ├─ Sales         50%  → pro-rata "Yang Menyerahkan/Menjual"
                          ├─ Admin         30%  → pro-rata "Nama Admin"
                          └─ Store Leader  20%  → utuh, satu orang per cabang
```

Semua angka di atas hanyalah nilai awal — semuanya bisa digeser di panel kiri.

**Kenapa pro-rata, bukan dibagi rata?** Karena orang yang menangani omset jasa
Rp 67 juta dan yang menangani Rp 1,6 juta tidak pantas menerima sama besar.
Pro-rata membuat insentif mengikuti kontribusi tanpa perlu tabel tarif baru.

**Kenapa Store Leader utuh?** Store Leader tidak muncul di kolom mana pun pada
data faktur; tanggung jawabnya atas seluruh cabang, jadi porsinya tidak dipecah.

---

## Menjalankan di komputer sendiri

```bash
pip install -r requirements.txt
streamlit run app.py
```

Buka `http://localhost:8501`, unggah ekspor **Rincian Faktur Penjualan**.

---

## Menaruh di GitHub lalu online lewat Streamlit Cloud

### 1. Buat repo di GitHub

Buka <https://github.com/new>, beri nama misalnya `simulasi-insentif-service`,
pilih **Private** bila datanya sensitif, lalu **Create repository**. Jangan
centang "Add a README" — sudah ada di sini.

### 2. Unggah kode

Dari folder ini:

```bash
git init
git add .
git commit -m "Simulasi insentif service MFlash"
git branch -M main
git remote add origin https://github.com/<akun-anda>/simulasi-insentif-service.git
git push -u origin main
```

Kalau GitHub meminta password, yang dipakai bukan password akun melainkan
**Personal Access Token**: Settings → Developer settings → Personal access
tokens → Tokens (classic) → Generate new token, centang `repo`.

Tidak terbiasa dengan git? Buka repo di GitHub, klik **Add file → Upload
files**, seret semua berkas dari folder ini, lalu **Commit changes**.

### 3. Deploy ke Streamlit Community Cloud (gratis)

1. Buka <https://share.streamlit.io> dan masuk dengan akun GitHub.
2. **Create app** → **Deploy a public app from GitHub**.
3. Isi: Repository `<akun-anda>/simulasi-insentif-service`, Branch `main`,
   Main file path `app.py`.
4. **Deploy**. Sekitar dua menit, aplikasi hidup di alamat
   `https://<nama>.streamlit.app`.

Setiap kali Anda `git push`, Streamlit Cloud otomatis memperbarui aplikasinya.

> Repo privat tetap bisa di-deploy, tetapi jumlah aplikasi privat di paket
> gratis terbatas. Karena aplikasi ini tidak menyimpan data apa pun (berkas
> hanya diproses di memori saat diunggah), repo publik pun aman — yang penting
> **jangan pernah commit berkas Excel berisi data pelanggan**. `.gitignore`
> sudah menghalangi `*.xlsx` ikut ter-commit.

---

## Isi repo

| Berkas | Isi |
|---|---|
| `app.py` | tampilan Streamlit |
| `insentif.py` | mesin perhitungan, terpisah supaya mudah diuji dan dipakai ulang |
| `uji.py` | uji cepat mesin perhitungan (`python uji.py`) |
| `requirements.txt` | daftar pustaka |
| `.streamlit/config.toml` | warna MFlash |

---

## Kolom yang dibaca dari ekspor

| Kolom | Dipakai untuk |
|---|---|
| `TGL FAKTUR` | menyaring periode |
| `KATEGORI BARANG` | mengambil baris **JASA** |
| `KATEGORI PENJUALAN` | menandai faktur service |
| `KATEGORI PELANGGAN` | opsi basis Member Reguler |
| `TOTAL HARGA` | nilai omset |
| `YANG MENYERAHKAN/MENJUAL` | porsi Sales |
| `NAMA ADMIN` | porsi Admin |

Nama kolom dicocokkan tanpa memperhatikan huruf besar/kecil dan tanda baca,
dan seluruh sheet ditelusuri — jadi ekspor dengan beberapa sheet tetap terbaca.

---

## Batas yang perlu diketahui

- Satu berkas = satu cabang. Untuk membandingkan antar cabang, jalankan
  bergantian.
- Omset jasa tanpa nama penyerah atau nama admin tetap masuk pool tetapi tidak
  bisa diatribusikan; nilainya ditampilkan di tab **Catatan data**.
- Nama dengan dua ejaan (mis. `ARIF FIKRI` dan `ARIF FIKRI KLENDER`) dihitung
  sebagai dua orang. Aplikasi menandainya, perbaikannya di sistem sumber.
- Sparepart pada faktur service **tidak** masuk pool — hanya baris `JASA`.
