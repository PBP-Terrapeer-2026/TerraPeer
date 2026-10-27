 let currentProfile = null;
  let currentLocation = {};
  let editingPlanId = null;
  let availablePots = [];
  let targetPlanId = null;
  let selectedCitySuggestion = null;

  document.getElementById("city-input").addEventListener("input", () => {
    selectedCitySuggestion = null;
  });

  function selectCitySuggestion(button) {
    const input = document.getElementById("city-input");
    input.value = button.dataset.input;
    selectedCitySuggestion = {
      input: button.dataset.input,
      latitude: Number(button.dataset.latitude), //NUmber? hey its not ts
      longitude: Number(button.dataset.longitude),
      name: button.dataset.name,
      country: button.dataset.country,
    };
    document.getElementById("city-suggestions").innerHTML = "";
  }

  function getCookie(name) {
    const v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)"); //im sorry this regex was generated (haven't learn about it yet)
    return v ? v.pop() : "";
  }
  const CSRF = getCookie("csrftoken");

  async function searchWeather() {
    const city = document.getElementById("city-input").value.trim();
    if (!city) return alert("Isi nama kota dulu ya!");

    setLoading("search-spin", true);
    try {
      const geoResults = selectedCitySuggestion?.input === city
        ? [selectedCitySuggestion]
        : await fetchGeo(city);
      if (!geoResults.length)
        throw new Error(`Lokasi "${city}" tidak ditemukan.`);
      const { latitude, longitude, name, country } = geoResults[0];
      currentLocation = {
        latitude,
        longitude,
        name: [name, country].filter(Boolean).join(", "),
      };

      const weather = await fetchWeather(latitude, longitude);
      const daily = weather.daily || {};
      const avg = (arr) => {
        const values = (arr || []).filter(Number.isFinite);
        return values.length
          ? values.reduce((sum, value) => sum + value, 0) / values.length
          : 0;
      };
      //weather data
      const humidArr = weather.hourly?.relative_humidity_2m || [];
      currentProfile = {
        avg_rain_mm: +avg(daily.precipitation_sum).toFixed(2),
        avg_temp_c: +avg(daily.temperature_2m_mean).toFixed(1),
        avg_radiation: +avg(daily.shortwave_radiation_sum).toFixed(1),
        avg_humidity: humidArr.length ? +avg(humidArr).toFixed(0) : 60,
      };

      const sumEl = document.getElementById("weather-summary");
      sumEl.innerHTML = `
      <span class="badge rounded-pill text-bg-success">🌧 Hujan: ${currentProfile.avg_rain_mm} mm/hari</span>
      <span class="badge rounded-pill text-bg-success">🌡 Suhu: ${currentProfile.avg_temp_c} °C</span>
      <span class="badge rounded-pill text-bg-success">☀️ Radiasi: ${currentProfile.avg_radiation} MJ/m²</span>
      <span class="badge rounded-pill text-bg-success">💧 Kelembapan: ${currentProfile.avg_humidity}%</span>
      <span class="badge rounded-pill text-bg-success">📍 ${escapeHtml(currentLocation.name)}</span>`;
      sumEl.classList.remove("d-none");
      await fetchRecommendations();
    } catch (err) {
      alert(err.message || "Gagal memuat data lokasi dan cuaca.");
    } finally {
      setLoading("search-spin", false);
    }
  }

  document.getElementById("weather-search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    searchWeather();
  });

  async function fetchRecommendations() {
    if (!currentProfile) return;
    const cityName = (currentLocation.name || "lokasi ini").split(",")[0].trim();
    document.getElementById("rekomendasi-title").textContent =
      `🌱 Rekomendasi tanaman di ${cityName}`;
    document.getElementById("rec-section").classList.remove("d-none");
    document.getElementById("rec-loading").classList.remove("d-none");
    document.getElementById("plant-grid").innerHTML = "";
    document.getElementById("rec-alert").innerHTML = "";

    try {
      const res = await fetch("/garden_planning/api/recommend/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
        body: JSON.stringify(currentProfile),
      });
      const data = await readApiResponse(res);
      document.getElementById("rec-loading").classList.add("d-none");
      // Filter info
      document.getElementById("filter-watering").textContent =
        data.filters.watering;
      document.getElementById("filter-sunlight").textContent =
        data.filters.sunlight;

      // Pot
      const pot = data.pot;
      document.getElementById("pot-name").textContent = pot.name;
      document.getElementById("pot-detail").textContent =
        `${pot.size_cm} cm · ${pot.material}`;

      // Tanaman grid
      const grid = document.getElementById("plant-grid");
      if (!data.plants.length) {
        grid.innerHTML =
          '<div class="col-12"><div class="alert alert-info mb-0">Tidak ada tanaman yang cocok dengan kondisi cuaca ini.</div></div>';
        return;
      }
      grid.innerHTML = data.plants
        .map(
          (p) => `
      <div class="col">
        <article class="card h-100 bg-light border-0 shadow-sm rounded-4 overflow-hidden">
          <div class="ratio ratio-4x3 bg-success-subtle">
            <img class="card-img-top object-fit-cover" src="${p.image_url || "https://placehold.co/600x450/eaf6ef/1b4032?text=Tanaman"}"
                 alt="${escapeHtml(p.name)}" loading="lazy" />
          </div>
          <div class="card-body d-flex flex-column p-3 p-lg-4">
            <h3 class="h6 fw-bold text-success-emphasis mb-2">${escapeHtml(p.name)}</h3>
            <p class="small text-secondary flex-grow-1 mb-3">${escapeHtml(p.description || "Deskripsi tanaman belum tersedia.")}</p>
            <p class="small text-secondary mb-3">💧 ${escapeHtml(p.watering)} · ☀️ ${escapeHtml(
              Array.isArray(p.sunlight) ? p.sunlight.join(", ") : p.sunlight,
            )}</p>
            <button class="btn btn-success rounded-pill fw-semibold w-100 mt-auto"
                    onclick="addToPlan(${Number(p.id)}, '${escapeHtml(p.name).replace(/'/g, "\\'")}')">
              + Tambah ke Rencana
            </button>
          </div>
        </article>
      </div>
    `,
        )
        .join("");
    } catch (err) {
      document.getElementById("rec-loading").classList.add("d-none");
      document.getElementById("rec-alert").innerHTML =
        `<div class="alert alert-danger">⚠️ ${escapeHtml(err.message || "Gagal memuat rekomendasi.")}</div>`;
    }
  }

  function showCreatePlan() {
    document.getElementById("create-plan-form").classList.remove("d-none");
  }
  function hidePlanForm() {
    document.getElementById("create-plan-form").classList.add("d-none");
  }

  function editPlan(id, button) {
    const li = button.closest(".plan-item");
    editingPlanId = id;
    document.getElementById("edit-plan-name").value = li.querySelector(".plan-item-name").textContent;
    document.getElementById("edit-plan-status").value = li.dataset.status || "planning";
    const modal = document.getElementById("edit-plan-modal");
    modal.classList.remove("d-none");
    modal.classList.add("d-flex");
  }

  function closeEditPlan() {
    const modal = document.getElementById("edit-plan-modal");
    modal.classList.add("d-none");
    modal.classList.remove("d-flex");
  }

  async function savePlanEdit() {
    const name = document.getElementById("edit-plan-name").value.trim();
    const status = document.getElementById("edit-plan-status").value;
    if (!name) return alert("Nama rencana wajib diisi.");
    const res = await fetch(`/garden_planning/api/plans/${editingPlanId}/`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
      body: JSON.stringify({ name, status }),
    });
    try {
      await readApiResponse(res);
      const li = document.querySelector(`#plan-list .plan-item[data-id="${editingPlanId}"]`);
      if (li) {
        li.dataset.status = status;
        li.querySelector(".plan-item-name").textContent = name;
        li.querySelector(".plan-status").outerHTML = planStatusBadge(status);
      }
      closeEditPlan();
    } catch (err) {
      alert(err.message);
    }
  }

  async function loadPots() {
    const list = document.getElementById("pot-list");
    try {
      const res = await fetch("/garden_planning/api/pots/", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      const data = await readApiResponse(res);
      availablePots = data.pots;
      list.innerHTML =
        data.pots
          .map(
            (
              p,
            ) => `<li class="d-flex flex-wrap align-items-center justify-content-between gap-3 p-3 rounded-3 border bg-light plan-item" data-id="${p.id}">
      <div><div class="fw-bold text-success-emphasis plan-item-name">${p.name}</div><div class="small text-body-secondary mt-1 plan-item-loc">${p.size_cm} cm · ${p.material || "material tidak disebutkan"}</div></div>
      <div class="d-flex flex-wrap gap-2"><button class="btn btn-outline-success btn-sm" onclick="editPot(${p.id}, this)">Edit</button>
      <button class="btn btn-danger btn-sm" onclick="deletePot(${p.id}, this)">Hapus</button></div></li>`,
          )
          .join("") || '<li class="small text-secondary">Belum ada pot.</li>';
    } catch (err) {
      list.innerHTML = `<li class="text-danger small">${escapeHtml(err.message)}</li>`;
    }
  }

  async function readApiResponse(res) {
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      if (res.redirected && /login/i.test(res.url))
        throw new Error("Sesi login berakhir. Silakan login kembali.");
      throw new Error(
        `Server tidak mengirim data JSON (HTTP ${res.status}). Muat ulang halaman dan coba lagi.`,
      );
    }
    let data;
    try {
      data = await res.json();
    } catch (_) {
      throw new Error(
        "Respons server tidak valid. Muat ulang halaman dan coba lagi.",
      );
    }
    if (!res.ok)
      throw new Error(data.error || `Permintaan gagal (HTTP ${res.status}).`);
    return data;
  }

  function escapeHtml(value) {
    return String(value).replace(
      /[&<>"']/g,
      (char) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[char],
    );
  }

  function planStatusInfo(status) {
    const statuses = {
      planning: { label: "Perencanaan", classes: "bg-secondary-subtle text-secondary-emphasis" },
      ready: { label: "Siap Tanam", classes: "bg-warning-subtle text-warning-emphasis" },
      planted: { label: "Sudah Ditanam", classes: "bg-success-subtle text-success-emphasis" },
    };
    return statuses[status] || statuses.planning;
  }

  function planStatusBadge(status) {
    const info = planStatusInfo(status);
    return `<span class="badge rounded-pill plan-status ${info.classes}">${info.label}</span>`;
  }

  function setPlanStatusBadge(element, status) {
    const info = planStatusInfo(status);
    element.textContent = info.label;
    element.className = `badge rounded-pill ${info.classes}`;
  }

  async function loadPlans() {
    const list = document.getElementById("plan-list");
    try {
      const res = await fetch("/garden_planning/api/plans/", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      const data = await readApiResponse(res);
      list.innerHTML = "";
      if (!data.plans.length) {
        list.innerHTML =
          '<li id="empty-plan" class="small text-secondary">Belum ada rencana. Klik "+ Rencana Baru" untuk mulai.</li>';
        return;
      }
      for (const plan of data.plans) {
        const li = document.createElement("li");
        li.className =
          "d-flex flex-wrap align-items-center justify-content-between gap-3 p-3 rounded-3 border bg-light plan-item";
        li.dataset.id = plan.id;
        li.dataset.latitude = plan.latitude;
        li.dataset.longitude = plan.longitude;
        li.dataset.status = plan.status || "planning";
        li.innerHTML = `<div><div class="d-flex align-items-center gap-2 flex-wrap"><div class="fw-bold text-success-emphasis plan-item-name">${escapeHtml(plan.name)}</div>${planStatusBadge(plan.status)}</div><div class="small text-body-secondary mt-1 plan-item-loc">${escapeHtml(plan.location_name || "—")}</div></div>
        <div class="d-flex flex-wrap gap-2"><button class="btn btn-outline-success btn-sm" onclick="editPlan(${plan.id}, this)">Edit</button>
        <button class="btn btn-outline-success btn-sm" onclick="viewPlan(${plan.id})">Lihat</button>
        <button class="btn btn-danger btn-sm" onclick="deletePlan(${plan.id}, this)">Hapus</button></div>`;
        list.appendChild(li);
      }
    } catch (err) {
      list.innerHTML = `<li class="text-danger small">${escapeHtml(err.message)}</li>`;
    }
  }

  async function createPot() {
    const name = document.getElementById("pot-name-input").value.trim();
    const size_cm = Number(document.getElementById("pot-size-input").value);
    const material = document.getElementById("pot-material-input").value.trim();
    const res = await fetch("/garden_planning/api/pots/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
      body: JSON.stringify({ name, size_cm, material }),
    });
    const data = await res.json();
    if (!res.ok) return alert(data.error || "Gagal membuat pot.");
    document.getElementById("pot-name-input").value = "";
    document.getElementById("pot-size-input").value = "";
    document.getElementById("pot-material-input").value = "";
    if (targetPlanId) {
      window.location.href = `/garden_planning/plans/${targetPlanId}/`;
      return;
    }
    await loadPots();
  }

  async function editPot(id, button) {
    const li = button.closest(".plan-item");
    const name = prompt(
      "Nama pot:",
      li.querySelector(".plan-item-name").textContent,
    );
    if (name === null || !name.trim()) return;
    const oldSize =
      li.querySelector(".plan-item-loc").textContent.match(/^\d+/)?.[0] || "30";
    const size_cm = Number(prompt("Ukuran pot (cm):", oldSize));
    if (!size_cm) return;
    const res = await fetch(`/garden_planning/api/pots/${id}/`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
      body: JSON.stringify({ name: name.trim(), size_cm }),
    });
    if (!res.ok) return alert("Gagal mengubah pot.");
    loadPots();
  }

  async function deletePot(id, button) {
    if (!confirm("Hapus pot ini?")) return;
    const res = await fetch(`/garden_planning/api/pots/${id}/`, {
      method: "DELETE",
      headers: { "X-CSRFToken": CSRF },
    });
    if (!res.ok) return alert("Gagal menghapus pot.");
    button.closest(".plan-item").remove();
  }

  async function createPlan() {
    const name = document.getElementById("plan-name").value.trim();
    if (!name) return alert("Isi nama rencana dulu!");

    const body = {
      name,
      location_name: currentLocation.name || "",
      latitude: currentLocation.latitude || 0,
      longitude: currentLocation.longitude || 0,
      environment_profile: currentProfile || {},
    };

    const res = await fetch("/garden_planning/api/plans/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) return alert(data.error || "Gagal membuat plan.");

    // Tambah ke DOM
    const emptyEl = document.getElementById("empty-plan");
    if (emptyEl) emptyEl.remove();

    const li = document.createElement("li");
    li.className =
      "d-flex flex-wrap align-items-center justify-content-between gap-3 p-3 rounded-3 border bg-light plan-item";
    li.dataset.id = data.id;
    li.dataset.latitude = body.latitude;
    li.dataset.longitude = body.longitude;
    li.dataset.status = data.status || "planning";
    li.innerHTML = `
    <div>
      <div class="d-flex align-items-center gap-2 flex-wrap"><div class="fw-bold text-success-emphasis plan-item-name">${escapeHtml(data.name)}</div>${planStatusBadge(data.status)}</div>
      <div class="small text-body-secondary mt-1 plan-item-loc">${body.location_name || "—"}</div>
    </div>
    <div class="d-flex flex-wrap gap-2">
      <button class="btn btn-outline-success btn-sm" onclick="editPlan(${data.id}, this)">Edit</button>
      <button class="btn btn-outline-success btn-sm" onclick="viewPlan(${data.id})">Lihat</button>
      <button class="btn btn-danger btn-sm" onclick="deletePlan(${data.id}, this)">Hapus</button>
    </div>
  `;
    document.getElementById("plan-list").appendChild(li);

    document.getElementById("plan-name").value = "";
    document.getElementById("plan-loc").value = "";
    hidePlanForm();
  }

  async function deletePlan(id, btn) {
    if (!confirm("Hapus rencana ini?")) return;
    const res = await fetch(`/garden_planning/api/plans/${id}/`, {
      method: "DELETE",
      headers: { "X-CSRFToken": CSRF },
    });
    if (res.ok) {
      const li = btn.closest(".plan-item");
      li.remove();
      if (!document.querySelectorAll("#plan-list .plan-item").length) {
        const ul = document.getElementById("plan-list");
        ul.innerHTML =
          '<li id="empty-plan" class="small text-secondary">Belum ada rencana.</li>';
      }
    }
  }

  function viewPlan(id) {
    window.location.href = `/garden_planning/plans/${id}/`;
  }

  async function loadPlanForRecommendations(id) {
    try {
      const response = await fetch(`/garden_planning/api/plans/${id}/`);
      const plan = await readApiResponse(response);
      targetPlanId = String(plan.id);
      currentLocation = {
        latitude: Number(plan.latitude),
        longitude: Number(plan.longitude),
        name: plan.location_name || "Lokasi plan",
      };
      currentProfile = plan.environment_profile || {};
      document.getElementById("city-input").value = currentLocation.name;
      const summary = document.getElementById("weather-summary");
      summary.innerHTML = `<span class="badge rounded-pill text-bg-success">📍 Rekomendasi untuk ${escapeHtml(currentLocation.name)}</span>`;
      summary.classList.remove("d-none");
      await fetchRecommendations();
    } catch (error) {
      alert(error.message || "Gagal memuat lokasi plan.");
    }
  }

  async function addToPlan(plantId, plantName) {
    const plans = [...document.querySelectorAll("#plan-list .plan-item")];
    if (!plans.length && !targetPlanId) {
      alert("Buat rencana dulu sebelum menambah tanaman!");
      return;
    }

    let planId;
    if (targetPlanId) {
      planId = targetPlanId;
    } else if (plans.length === 1) {
      planId = plans[0].dataset.id;
    } else {
      const options = plans
        .map(
          (li, i) =>
            `${i + 1}. ${li.querySelector(".plan-item-name").textContent}`,
        )
        .join("\n");
      const idx = parseInt(prompt(`Pilih nomor rencana:\n${options}`), 10) - 1;
      if (isNaN(idx) || idx < 0 || idx >= plans.length) return;
      planId = plans[idx].dataset.id;
    }

    const selectedPlan = plans.find((plan) => plan.dataset.id === String(planId));
    const planLatitude = Number(selectedPlan?.dataset.latitude ?? currentLocation.latitude);
    const planLongitude = Number(selectedPlan?.dataset.longitude ?? currentLocation.longitude);
    if (
      !Number.isFinite(currentLocation.latitude) ||
      !Number.isFinite(currentLocation.longitude)
    ) {
      return alert("Cari cuaca untuk lokasi tanaman terlebih dahulu.");
    }
    if (
      !Number.isFinite(planLatitude) ||
      !Number.isFinite(planLongitude) ||
      Math.abs(currentLocation.latitude - planLatitude) > 0.01 ||
      Math.abs(currentLocation.longitude - planLongitude) > 0.01
    ) {
      return alert(
        `Lokasi rekomendasi (${currentLocation.name || "saat ini"}) tidak sama dengan lokasi plan (${selectedPlan?.querySelector(".plan-item-loc")?.textContent || currentLocation.name || "tidak diketahui"}). Tanaman tidak dapat ditambahkan.`,
      );
    }

    const res = await fetch(`/garden_planning/api/plans/${planId}/items/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
      body: JSON.stringify({
        plant_id: plantId,
        quantity: 1,
        recommendation_latitude: currentLocation.latitude,
        recommendation_longitude: currentLocation.longitude,
      }),
    });
    try {
      await readApiResponse(res);
      alert(`✅ "${plantName}" berhasil ditambahkan ke rencana!`);
    } catch (err) {
      alert(err.message || "Gagal menambahkan tanaman.");
    }
  }

  function setLoading(id, on) {
    document.getElementById(id).classList.toggle("d-none", !on);
  }
  loadPots();
  loadPlans();
  const pageParams = new URLSearchParams(window.location.search);
  const requestedPlanId = pageParams.get("plan_id");
  if (requestedPlanId) loadPlanForRecommendations(requestedPlanId);
  if (pageParams.has("add_pot")) {
    const potInput = document.getElementById("pot-name-input");
    potInput.scrollIntoView({ behavior: "smooth", block: "center" });
    potInput.focus({ preventScroll: true });
  }

  
