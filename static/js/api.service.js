async function fetchGeo(namaKota) {
  const params = new URLSearchParams({
    name: namaKota,
    count: "5",
    language: "id",
    format: "json",
  });
  const url = `https://geocoding-api.open-meteo.com/v1/search?${params}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok)
      throw new Error(
        `Layanan pencarian lokasi gagal (HTTP ${response.status}).`,
      );
    const data = await response.json();
    return data.results ?? [];
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error("Pencarian lokasi melewati batas waktu. Coba lagi.");
    throw new Error(
      "Tidak dapat terhubung ke layanan pencarian lokasi. Periksa koneksi internet.",
    );
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchWeather(latitude, longitude) {
  const params = new URLSearchParams({
    latitude,
    longitude,
    timezone: "auto",
    forecast_days: 7,
    daily:
      "temperature_2m_mean,precipitation_sum,shortwave_radiation_sum,weather_code,temperature_2m_max,temperature_2m_min,precipitation_hours",
    hourly: "relative_humidity_2m",
  });

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(
      `https://api.open-meteo.com/v1/forecast?${params}`,
      { signal: controller.signal },
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    if (err.name === "AbortError")
      throw new Error(
        "Pengambilan data cuaca melewati batas waktu. Coba lagi.",
      );
    throw new Error(
      "Tidak dapat mengambil data cuaca. Periksa koneksi internet.",
    );
  } finally {
    clearTimeout(timeout);
  }
}
