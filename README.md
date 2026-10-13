# HexaCare

Prototipe website crowdfunding bantuan sosial menggunakan Python dan SQLite.

## Status dan batasan

Proyek ini menyediakan registrasi, login, daftar event, pencatatan donasi,
receipt, dan laporan total donasi. Transaksi dari form langsung dicatat sebagai
`SUCCESS` di database; belum ada integrasi payment gateway atau verifikasi
transfer. Status tersebut menunjukkan catatan aplikasi, bukan bukti pembayaran.
Data event dan jumlah awal donasi disediakan sebagai data demo. Proyek ini
belum membuktikan penyaluran bantuan atau pemerataan distribusinya.

## Struktur

- `Home/` halaman utama.
- `Login/` halaman login.
- `Registrasi/` halaman registrasi.
- `Tampilan Event/` halaman daftar event bantuan.
- `Donasi/` halaman form donasi.
- `Proses Transaksi/` halaman receipt dan status transaksi.
- `Total Donasi/` halaman laporan total donasi.
- `assets/` styling website.
- `database/` data SQLite runtime, jangan dihapus saat update.

## Menjalankan

Windows:

```bat
self.cmd
```

Pterodactyl atau Linux hosting:

```bash
python3 app.py
```

App membaca `PORT` dari environment. Jika tidak ada, default `8080`.

## Database

SQLite dibuat otomatis di:

```text
database/hexacare.sqlite3
```

Saat update website, hapus/upload ulang semua file kecuali folder `database/` agar user, event, dan transaksi tetap aman.

