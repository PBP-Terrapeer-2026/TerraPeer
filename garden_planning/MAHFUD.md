# AI Disclosure

-Saya meminta AI untuk memberikan contoh XSS cleaner untuk form bawaan django karena apa yang ada di tutorial belum cukup untuk mencakup semua test coverage
-Design-design seperti penggunaan row dan flexbox yang ada
-Penggunaan params modern (karena tadinya saya memakai URI parser)
-Fetching API di back-end (django) dibantu oleh AI karena dalam tutorial yang dicontohkan adalah fetch oleh javascript melalui AJAX
-Pembuatan kategori pot yang merupakan hardcode

---

# Fitur Garden Planning

- **Cari lokasi dan cuaca:** pengguna mencari kota lalu melihat ringkasan kondisi cuaca lokasi.
- **Rekomendasi tanaman:** aplikasi mengambil data tanaman dari API Perenual berdasarkan kondisi cuaca, menampilkan deskripsi dan kebutuhan tanaman, serta menyarankan pot.
- **Kelola rencana tanam:** pengguna dapat membuat, melihat, mengubah nama dan status, serta menghapus rencana. Ringkasan rencana menampilkan tanaman, kebutuhan pot, dan daftar belanja.
- **Kelola pot:** pengguna dapat menambahkan pot melalui Django Form, memilih bahan pot, lalu mengedit atau menghapus pot. Daftar pot dimuat dan diperbarui menggunakan HTMX.
- **Tambah tanaman ke rencana tanam:** aplikasi menolak penambahan jika lokasi rekomendasi berbeda dari lokasi rencana.
- **Keamanan tampilan:** teks dinamis di-escape sebelum dimasukkan ke HTML; form pot juga membersihkan tag HTML dan konten aktif pada nama pot.
