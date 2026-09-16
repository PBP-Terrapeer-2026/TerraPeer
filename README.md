# TerraPeer

---

# DESKRIPSI APLIKASI

TerraPeer adalah website yang dirancang untuk mendampingi pengguna dalam menanam tumbuhan sesuai dengan kondisi lingkungan. Website ini memberikan rekomendasi jenis tumbuhan yang cocok, membantu perencanaan dan perawatan, serta mencatat perkembangan dari tumbuhan.
Di langkah awal, pengguna membuat profil ruang tanam yang mencakup spesifikasi media tanam, daerah penanaman, dan kemampuan dalam melakukan perawatan. Profil tersebut akan menjadi dasar TerraPeer dalam merekomendasikan tumbuhan yang realistis untuk ditanam beserta penjelasan lengkap. Dari situ, pengguna bisa memilih tumbuhan untuk dimasukkan ke Garden Plan. Setelah dipilih, website akan memberikan ringkasan rencana.
Saat pengguna sudah membeli bibit dan mempersiapkan penanaman, pengguna bisa set status dari tumbuhan tersebut menjadi Active Plant. Dari situ, fokus website berpindah menjadi pendampingan perawatan harian, website akan menampilkan tugas dan instruksi perawatan. Perkembangan tanaman akan dicatat, pengguna cukup memilih opsi kondisi tanaman seperti tumbuh normal, layu, dan sebagainya. Di beberapa periode waktu, TerraPeer akan memberikan ringkasan evaluasi kebun.

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
