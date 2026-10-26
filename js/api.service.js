async function fetchGeo(namaKota) {
  let count = 1;
  const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(namaKota)}&count=${count}`;
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    count++;
    return data.results ?? [];
  } catch (error) {
    console.error("Error fetching geocoding data:", error);
    return [];
  }
}

async function fetchWeather(latitude, longitude) {
  const params = new URLSearchParams({
    latitude,
    longitude,
    timezone: "auto",
    forecast_days: 7,
    daily: "temperature_2m_mean,precipitation_sum,shortwave_radiation_sum",
    hourly: "relative_humidity_2m",
  });
  try {
    const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Weather gagal:", err);
    return null;
  }
}
