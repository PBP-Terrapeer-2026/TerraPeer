# TerraPeer

---

# DESKRIPSI APLIKASI

TerraPeer adalah website yang dirancang untuk mendampingi pengguna dalam menanam tumbuhan sesuai dengan kondisi lingkungan. Website ini memberikan rekomendasi jenis tumbuhan yang cocok, membantu perencanaan dan perawatan, serta mencatat perkembangan dari tumbuhan.
Di langkah awal, pengguna membuat profil ruang tanam yang mencakup spesifikasi media tanam, daerah penanaman, dan kemampuan dalam melakukan perawatan. Profil tersebut akan menjadi dasar TerraPeer dalam merekomendasikan tumbuhan yang realistis untuk ditanam beserta penjelasan lengkap. Dari situ, pengguna bisa memilih tumbuhan untuk dimasukkan ke Garden Plan. Setelah dipilih, website akan memberikan ringkasan rencana.
Saat pengguna sudah membeli bibit dan mempersiapkan penanaman, pengguna bisa set status dari tumbuhan tersebut menjadi Active Plant. Dari situ, fokus website berpindah menjadi pendampingan perawatan harian, website akan menampilkan tugas dan instruksi perawatan. Perkembangan tanaman akan dicatat, pengguna cukup memilih opsi kondisi tanaman seperti tumbuh normal, layu, dan sebagainya. Di beberapa periode waktu, TerraPeer akan memberikan ringkasan evaluasi kebun.

# DESAIN UI/UX

Desain UI/UX TerraPeer: [Figma TerraPeer](https://www.figma.com/design/fZa8nxPXXGqgu0ytl6WFhY/Terrapeer?)

Password akses: `TerrapeerPBP5F`

# PUBLIC API YANG DIPAKAI

https://open-meteo.com/en/docs/geocoding-api - Open Meteo Geocoding API
https://open-meteo.com/en/docs - Open Meteo Forecasting API
https://www.perenual.com/docs/api - Perenual API

# PERAN PENGGUNA

TerraPeer memiliki dua jenis pengguna utama, yaitu:

1. Guest
   Guest adalah pengguna yang belum melakukan login ke TerraPeer. Guest dapat melihat informasi umum yang tersedia secara publik, seperti informasi mengenai tanaman dan gambaran (preview) mengenai fitur TerraPeer. Guest tidak dapat mengakses maupun mengelola data tanaman yang bersifat pribadi.

2. Registered User
   Registered User adalah pengguna yang telah memiliki akun dan melakukan login. Pengguna ini merupakan pengguna utama TerraPeer yang dapat menggunakan seluruh fitur personal gardening assistant.

Registered User dapat:
Membuat dan mengelola profil atau Growing Space
Mengeksplorasi atau mencari tanaman
Memperoleh rekomendasi tanaman berdasarkan kondisi Growing Space
Membuat dan mengelola Garden Plans
Menambahkan tanaman yang telah ditanam ke dalam My Garden
Mengelola kegiatan perawatan tanaman
Mencatat observasi dan perkembangan tanaman
Melihat kembali riwayat serta perkembangan tanaman

Setiap data tanaman yang bersifat personal, seperti Growing Spaces, Garden Plans, Care Tasks, dan My Garden, hanya dapat diakses dan dikelola oleh pengguna yang bersangkutan.

1. Garden Setup
2. Garden Planning
3. My Plants
4. Plant Care
5. Garden Journal

# DAFTAR MODUL RENCANA DAN PEMBAGIAN PER ANGGOTA

1. Garden Setup - Jotham Seanvedi Takin Allo
   Garden Setup adalah tahap awal dari interaksi pengguna. Pada tahap ini, Pengguna memasukkan input berupa kondisi lingkungan tempat dimana tanaman akan ditanam. Input berupa jenis ruangan, lokasi, durasi cahaya matahari, curah hujan di area, ketersediaan penyangga, media tanam, dan frekuensi perawatan tanamannya. Data dari input ini akan dilanjutkan kepada sistem untuk mengetahui kondisi ruang tanam pengguna seperti apa.
2. Garden Planning - Ayyasi
   Pada tahap Garden Planning, sistem akan menentukan jenis-jenis tanaman yang direkomendasikan untuk ditanam pengguna berdasarkan hasil mengolah data berdasarkan dari kondisi lingkungan pengguna.
   Pada tahap ini, sistem akan mengembalikan output berupa rekomendasi pot untuk menanam, tanaman yang direkomendasikan, dan juga tujuan atau manfaat dari tanaman tersebut. Setelah mendapatkan output tersebut, user dapat menambahkan plan, menambahkan tanaman, menambahkan jenis pot, sekaligus fitur untuk menghapus dan mengedit data tersebut.

3. My Plants - Muhammad Farel Ammar
   Tahap dari My Plants ini berbeda dengan garden planning. Tahap ini akan membantu mengelola dan memelihara tanaman pengguna yang benar-benar sudah ditanam sebelumnya. Tahap ini akan mengelola data pengguna berupa jenis tanaman, tanggal mulai ditanam, sumber garden plan (jika ada), tahap pertumbuhan, dan status tanaman. Data-data tersebut digunakan untuk membantu memonitoring tanaman pengguna yang telah ditanam sebelum menggunakan website ini. Tahap ini akan memonitoring dari tahap Growing, Flowering, Fruiting, Harvesting, Finished.

4. Plant Care - Nashri Khalid
   Plant Care membantu pengguna mengelola tugas perawatan untuk tanaman yang sudah aktif, seperti menyiram, memangkas, memeriksa kondisi daun, penyangga, nutrisi, dan kesiapan panen. Pengguna dapat membuat, melihat, mengubah, menyelesaikan, menghapus, serta memfilter tugas berdasarkan waktu atau tanaman tertentu. Modul ini juga menampilkan informasi cuaca sebagai konteks pendukung agar pengguna lebih mudah menentukan apa yang perlu diperiksa dan kapan melakukannya.
5. Garden Journal - Adinda Pika Fauziah
   Garden Journal membantu pengguna mencatat perkembangan tanaman aktif, seperti pertumbuhan, pembungaan, panen, atau masalah yang terjadi. Catatan ditampilkan dalam bentuk timeline dan dapat dilengkapi tanggal, keterangan, jumlah panen, serta konteks cuaca pada waktu tertentu. Modul ini membantu pengguna melihat riwayat kebun dan mengevaluasi pengalaman sebelumnya untuk perencanaan berikutnya.

# IMPLEMENTASI MY PLANTS (Muhammad Farel Ammar)

Modul My Plants ada di `/my-plants/` (wajib login). Jalankan `python manage.py migrate` lalu `python manage.py test`.

Untuk menjalankan pengujian browser, aktifkan virtualenv Python dan siapkan Node.js:

```powershell
npm --prefix tests/browser install
npm --prefix tests/browser exec -- playwright install chromium
npm --prefix tests/browser test
```

Pencarian spesies memerlukan `PERENUAL_API_KEY` pada environment lokal/PWS. Tanpa key, spesies masih bisa diisi manual.

OpenAI Codex digunakan untuk membantu analisis, implementasi, dan pengujian. Perubahan diverifikasi menggunakan test Django serta pengujian browser.

| Ketentuan | Implementasi |
| --- | --- |
| Models | `my_plants.Plant`, `my_plants.PlantCheckIn`, dan `my_plants.PlantPhoto` (buatan sendiri), `User` dari Django sebagai pemilik. `Plant` disediakan untuk dipakai Plant Care dan Journal lewat ForeignKey. |
| Views + CRUD | Create, read (daftar + detail), update (edit + ubah tahap), delete (konfirmasi POST). Setiap operasi tulis bisa merespons HTML atau JSON (`Accept: application/json`); ada endpoint `api/` dan `api/<id>/`. |
| Template | `base.html` + `partials/header.html`, `partials/footer.html`, `partials/messages.html`; template modul di `templates/my_plants/`. Bootstrap 5.3.8 disimpan lokal di `static/vendor/bootstrap/`. |
| Form | `PlantForm`, `StageForm`, `PlantFilterForm`, `CheckInForm` dengan validasi server (tanggal tidak di masa depan, tahap valid, panjang catatan). |
| AJAX | Filter/sort/pagination tanpa reload, ubah tahap, simpan/hapus check-in, hapus dari modal, dan pencarian spesies Perenual memakai `fetch()`. |
| Filter autentikasi | Semua URL My Plants `login_required`; data selalu diambil lewat `Plant.objects.for_user(request.user)` sehingga ID milik akun lain menghasilkan 404. Navbar hanya menampilkan menu modul untuk pengguna yang login. |
| Filter data database | Pencarian nama/spesies, tahap tumbuh, status Active/Finished, dan urutan (terbaru, terlama, nama, paling lama tumbuh). |
| Foto & recap | Foto opsional saat menambah tanaman, foto **wajib** setiap ganti tahap, photo diary, dan halaman *growing recap* (durasi tiap tahap, foto per tahap, then-and-now) saat tanaman Finished. Foto disimpan di database (bukan folder media) agar aman di PWS. |

Desain UI/UX baru tersedia di file Figma TerraPeer (frame "(TerraPeer — …)").

---

# CHANGELOG

- 15 September, initial commit
- 29 September, inisisasi tampilan awal web
- 2 Oktober, Adding base template (header, footer, navbar) and show main page
- 21 Oktober, Refactoring auth page and fix user login
- 24 Oktober, Fixing cookie session timer
- 26 Oktober, Bootstrap layout partials, auth redesign, and My Plants module (CRUD, AJAX, check-ins)
- 26 Oktober, My Plants photo diary, required stage photos and growing recap


# IMPLEMENTASI MODUL GARDEN JOURNAL (Adinda Pika)

Garden Journal merupakan modul pada TerraPeer yang memungkinkan pengguna mencatat, mengelola, dan memantau perkembangan tanaman yang dimiliki. Modul ini berfungsi sebagai jurnal digital untuk mendokumentasikan berbagai aktivitas berkebun, mulai dari pertumbuhan tanaman, pembungaan, panen, hingga permasalahan yang ditemukan selama proses perawatan.

Setiap entri jurnal terhubung dengan tanaman milik pengguna melalui modul My Plants dan menyimpan informasi berupa tanggal pencatatan, jenis milestone, judul, catatan perkembangan, detail panen, serta kondisi cuaca yang diamati. Modul ini juga menyediakan fitur pencarian, filter, timeline, dan evaluasi bulanan untuk membantu pengguna melihat perkembangan aktivitas berkebun dari waktu ke waktu.

## Fitur yang Dikembangkan

- Create Journal Entry: membuat catatan jurnal baru dengan memilih tanaman dari koleksi My Plants, menentukan tanggal, jenis milestone, judul, dan progress notes.

- Read Journal Entries: menampilkan catatan jurnal dalam bentuk timeline yang responsif, dengan informasi tanaman, tanggal, jenis aktivitas, serta detail catatan.

- Update Journal Entry: memperbarui informasi jurnal yang sudah dibuat oleh pengguna.

- Delete Journal Entry: menghapus catatan jurnal yang sudah tidak diperlukan.

- My Plants Integration: menghubungkan Garden Journal dengan model `Plant` dari modul My Plants melalui ForeignKey. Pengguna hanya dapat memilih tanaman yang dimiliki melalui queryset yang dibatasi berdasarkan pengguna yang sedang login. Nama tanaman juga disimpan dalam `plant_name` sebagai snapshot untuk mempertahankan informasi historis jurnal.

- Milestone Categories: menyediakan lima jenis pencatatan aktivitas berkebun:
  - Growth
  - Flowering
  - Harvest
  - Pest or Disease
  - Other

- Conditional Harvest Details: menampilkan bagian Harvest Details ketika pengguna memilih milestone `Harvest`. Bagian ini mencatat jumlah hasil panen dan satuannya. Validasi memastikan jumlah panen diisi dan tidak bernilai negatif.

- Search & Filter: memungkinkan pengguna mencari jurnal berdasarkan nama tanaman, judul, catatan perkembangan, dan catatan cuaca. Pengguna juga dapat memfilter entri berdasarkan tanaman, jenis milestone, dan periode waktu (30 hari, 3 bulan, 6 bulan, atau seluruh waktu).

- HTMX Filtering: menerapkan HTMX untuk memperbarui hasil pencarian dan filter pada bagian timeline tanpa harus memuat ulang seluruh halaman. URL juga diperbarui menggunakan `hx-push-url`.

- Responsive Timeline Interface: menyediakan tampilan timeline dan form yang responsif menggunakan Bootstrap 5.3.8, dengan komponen visual khusus untuk Garden Journal.

- Monthly Garden Evaluation: menyediakan halaman evaluasi bulanan yang merangkum aktivitas berkebun berdasarkan bulan dan tahun yang dipilih. Evaluasi mencakup jumlah entri jurnal, aktivitas panen, permasalahan tanaman, perkembangan, pembungaan, ringkasan aktivitas mingguan, dan ringkasan berdasarkan tanaman.

- Weather Condition Selection: memungkinkan pengguna mencatat kondisi cuaca secara manual melalui pilihan kategori yang disertai ikon:
  - Sunny
  - Partly Cloudy
  - Cloudy
  - Light Rain
  - Heavy Rain
  - Stormy
  - Foggy
  - Windy
  - Hot
  - Other

- Additional Weather Notes: menyediakan kolom catatan cuaca tambahan secara opsional untuk menyimpan informasi seperti kondisi lingkungan atau pengamatan cuaca lainnya.

- Weather Context: menampilkan kondisi cuaca terbaru yang tercatat pada halaman utama Garden Journal, termasuk kategori kondisi cuaca, catatan tambahan jika tersedia, dan tanggal pencatatan.

- Access Control: membatasi akses dan pengelolaan entri jurnal berdasarkan pengguna yang sedang login. Pengguna tidak dapat mengelola entri milik pengguna lain.

## Model dan Struktur Data

Garden Journal menggunakan model `GardenJournalEntry` pada `main/models.py`.

Model ini menyimpan beberapa informasi utama:

| Field | Keterangan |
|---|---|
| `user` | Pengguna pemilik catatan jurnal |
| `plant` | Relasi ForeignKey ke model `Plant` pada modul My Plants |
| `plant_name` | Snapshot nama tanaman untuk mempertahankan riwayat jurnal |
| `entry_date` | Tanggal pencatatan jurnal |
| `entry_type` | Jenis milestone atau aktivitas berkebun |
| `title` | Judul catatan jurnal |
| `notes` | Catatan perkembangan atau pengamatan tanaman |
| `harvest_quantity` | Jumlah hasil panen, jika jenis entri adalah Harvest |
| `harvest_unit` | Satuan jumlah hasil panen |
| `weather_condition` | Kategori kondisi cuaca yang diamati |
| `weather_summary` | Catatan tambahan mengenai kondisi cuaca |
| `created_at` | Waktu pembuatan entri |
| `updated_at` | Waktu pembaruan terakhir |

Relasi `plant` menggunakan `on_delete=models.PROTECT` agar tanaman tidak dapat dihapus ketika masih direferensikan oleh entri jurnal. Sementara itu, `plant_name` menyimpan snapshot nama tanaman sehingga informasi nama historis tetap tersedia.

## Rute Garden Journal

| Rute / URL Name | Fungsi |
|---|---|
| `/garden-journal/` | Halaman utama Garden Journal, menampilkan timeline, pencarian, filter, dan Weather Context |
| `garden_journal_create` | Membuka form untuk membuat entri jurnal |
| `garden_journal_evaluation` | Menampilkan evaluasi aktivitas berkebun bulanan |
| `garden_journal` | Route halaman utama yang digunakan untuk navigasi kembali ke Garden Journal |

Selain halaman utama, modul juga menyediakan endpoint untuk operasi pembuatan, pengubahan, dan penghapusan entri jurnal.

## Pengujian Garden Journal

Pengujian dilakukan menggunakan Django testing framework untuk memastikan fungsionalitas dan integrasi modul berjalan sesuai kebutuhan.

Perintah untuk menjalankan pemeriksaan dan pengujian:

```bash
python manage.py check
python manage.py test main
python manage.py makemigrations --check
```

Pengujian terakhir pada branch `feat/garden-journal` menghasilkan:

- **27 tests**
- **27 tests passed**
- **0 test failures**
- Django system check: no issues identified.

Pengujian juga dilakukan secara manual pada browser untuk memeriksa pembuatan dan pengelolaan entri jurnal, pemilihan tanaman dari My Plants, filtering timeline, tampilan evaluasi bulanan, serta penyimpanan dan penampilan kondisi cuaca.

Hasil pengujian merupakan kondisi pada branch saat pengembangan dilakukan. Seluruh pengujian tetap perlu dijalankan kembali setelah integrasi dengan branch utama karena perubahan dari modul lain dapat memengaruhi hasil integrasi.

## Changelog Pengembangan

Berikut rangkuman perubahan berdasarkan riwayat commit pada branch `feat/garden-journal`:

| Commit | Perubahan |
|---|---|
| `94199de` | Implementasi awal fitur pembuatan entri Garden Journal dan styling |
| `2ccf0d1` | Penambahan pengujian akses jurnal dan operasi CRUD |
| `f4afb99` | Penyesuaian bahasa pesan keberhasilan |
| `bb53b86` | Integrasi Bootstrap 5.3.8 |
| `2f3a578` | Penambahan fitur filtering entri jurnal |
| `3d9b740` | Implementasi responsive timeline layout |
| `32a05a9` | Penyempurnaan styling form entri jurnal |
| `77cea2e` | Perbaikan tampilan ikon milestone |
| `03484ed` | Implementasi evaluasi bulanan Garden Journal |
| `3449e8e` | Penambahan pengujian Garden Evaluation |
| `1c80c5a` | Implementasi filtering menggunakan HTMX |
| `3527d32` | Integrasi entri jurnal dengan modul My Plants |
| `798dc37` | Implementasi pemilihan kondisi cuaca pada Garden Journal |

## Catatan Integrasi dan Pengembangan

Garden Journal terintegrasi dengan modul My Plants untuk memastikan setiap catatan jurnal berkaitan dengan tanaman yang dimiliki pengguna.


## AI USAGE DISCLOSURE

ChatGPT digunakan sebagai alat bantu selama proses pengembangan Garden Journal, terutama untuk membantu peninjauan kode serta menelusuri kesalahan pada kode

Saran yang dihasilkan AI disesuaikan dengan struktur proyek TerraPeer serta saya pilih pilih lagi masukannya. Implementasi dan hasil akhirnya tetap memerlukan verifikasi saya terhadap kode asli dan hasil integrasi dengan pekerjaan anggota tim lainnya.
