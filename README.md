# HexaCare

Trusted Crowdfunding Platform for Equal Social Aid Distribution.

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

