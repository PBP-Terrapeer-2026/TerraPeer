let currentProfile = null;
let currentLocation = {};
let editingPlanId = null;
let targetPlanId = null;
let selectedCitySuggestion = null;
const actionModalElement = document.getElementById("action-modal");
const actionModal = bootstrap.Modal.getOrCreateInstance(actionModalElement);
let actionModalResolver = null;

function showFeedback(message, type = "danger") {
  const feedback = document.getElementById("garden-feedback");
  feedback.className = `alert alert-${type}`;
  feedback.textContent = message;
}

function showActionModal({ title, message = "", fields = [], submitLabel = "Continue" }) {
  return new Promise((resolve) => {
    actionModalResolver = resolve;
    document.getElementById("action-modal-title").textContent = title;
    document.getElementById("action-modal-message").textContent = message;
    document.getElementById("action-modal-submit").textContent = submitLabel;
    document.getElementById("action-modal-feedback").classList.add("d-none");
    const container = document.getElementById("action-modal-fields");
    container.replaceChildren();

    for (const field of fields) {
      const wrapper = document.createElement("div");
      const label = document.createElement("label");
      label.className = "form-label";
      label.htmlFor = `action-field-${field.name}`;
      label.textContent = field.label;
      let input;
      if (field.options) {
        input = document.createElement("select");
        input.className = "form-select";
        for (const optionData of field.options) {
          const option = document.createElement("option");
          option.value = optionData.value;
          option.textContent = optionData.label;
          input.appendChild(option);
        }
      } else {
        input = document.createElement("input");
        input.type = field.type || "text";
        input.className = "form-control";
        if (field.min !== undefined) input.min = field.min;
      }
      input.id = `action-field-${field.name}`;
      input.name = field.name;
      input.value = field.value ?? "";
      input.required = field.required !== false;
      wrapper.append(label, input);
      container.appendChild(wrapper);
    }

    actionModal.show();
  });
}

document.getElementById("action-modal-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!event.currentTarget.reportValidity()) return;
  if (actionModalResolver) {
    actionModalResolver(Object.fromEntries(new FormData(event.currentTarget)));
    actionModalResolver = null;
  }
  actionModal.hide();
});

actionModalElement.addEventListener("hidden.bs.modal", () => {
  if (actionModalResolver) {
    actionModalResolver(null);
    actionModalResolver = null;
  }
});

document.getElementById("city-input").addEventListener("input", () => {
  selectedCitySuggestion = null;
  document.getElementById("refresh-button").disabled = true;
});

document.getElementById("plant-grid").addEventListener("click", (event) => {
  const button = event.target.closest("[data-add-plant]");
  if (!button) return;
  addToPlan(Number(button.dataset.plantId), button.dataset.plantName);
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
  if (!city) return showFeedback("Enter a city name first.");

  document.getElementById("refresh-button").disabled = true;
  setLoading("search-spin", true);
  try {
    const geoResults =
      selectedCitySuggestion?.input === city
        ? [selectedCitySuggestion]
        : await fetchGeo(city);
    if (!geoResults.length)
      throw new Error(`Location "${city}" was not found.`);
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
      <span class="badge rounded-pill text-bg-success">Rain: ${currentProfile.avg_rain_mm} mm/day</span>
      <span class="badge rounded-pill text-bg-success">Temperature: ${currentProfile.avg_temp_c} °C</span>
      <span class="badge rounded-pill text-bg-success">Radiation: ${currentProfile.avg_radiation} MJ/m²</span>
      <span class="badge rounded-pill text-bg-success">Humidity: ${currentProfile.avg_humidity}%</span>
      <span class="badge rounded-pill text-bg-success">${escapeHtml(currentLocation.name)}</span>`;
    sumEl.classList.remove("d-none");
    document.getElementById("refresh-button").disabled = false;
    showFeedback("Weather loaded successfully.", "success");
    await fetchRecommendations();
  } catch (err) {
    showFeedback(err.message || "Could not load location and weather data.");
  } finally {
    setLoading("search-spin", false);
  }
}

document
  .getElementById("weather-search-form")
  .addEventListener("submit", (event) => {
    event.preventDefault();
    searchWeather();
  });

async function fetchRecommendations() {
  if (!currentProfile) return;
  const cityName = (currentLocation.name || "this location").split(",")[0].trim();
  document.getElementById("rekomendasi-title").textContent =
    `Plant recommendations for ${cityName}`;
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
    document.getElementById("filter-watering").textContent =
      data.filters.watering;
    document.getElementById("filter-sunlight").textContent =
      data.filters.sunlight;

    const pot = data.pot;
    document.getElementById("pot-name").textContent = pot.name;
    document.getElementById("pot-detail").textContent =
      `${pot.size_cm} cm · ${pot.material}`;

    const grid = document.getElementById("plant-grid");
    if (!data.plants.length) {
      grid.innerHTML =
        '<div class="col-12"><div class="alert alert-info mb-0">No plants match this weather profile.</div></div>';
      return;
    }
    grid.innerHTML = data.plants
      .map(
        (p) => `
      <div class="col">
        <article class="card h-100 bg-light border-0 shadow-sm rounded-4 overflow-hidden">
          <div class="ratio ratio-4x3 bg-success-subtle">
            <img class="card-img-top object-fit-cover" src="${escapeHtml(p.image_url || "https://placehold.co/600x450/eaf6ef/1b4032?text=Tanaman")}" 
                 alt="${escapeHtml(p.name)}" loading="lazy" onerror="this.onerror=null;this.src='https://placehold.co/600x450/eaf6ef/1b4032?text=Tanaman'" />
          </div>
          <div class="card-body d-flex flex-column p-3 p-lg-4">
            <h3 class="h6 fw-bold text-success-emphasis mb-2">${escapeHtml(p.name)}</h3>
            <p class="small text-secondary flex-grow-1 mb-3">${escapeHtml(p.description || "Plant description is not available.")}</p>
            <p class="small text-secondary mb-3">💧 ${escapeHtml(p.watering)} · ☀️ ${escapeHtml(
              Array.isArray(p.sunlight) ? p.sunlight.join(", ") : p.sunlight,
            )}</p>
            <button class="btn btn-success rounded-pill fw-semibold w-100 mt-auto"
                    type="button" data-add-plant data-plant-id="${Number(p.id)}"
                    data-plant-name="${escapeHtml(p.name)}">
              + Add to plan
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
      `<div class="alert alert-danger">${escapeHtml(err.message || "Could not load recommendations.")}</div>`;
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
  document.getElementById("edit-plan-name").value =
    li.querySelector(".plan-item-name").textContent;
  document.getElementById("edit-plan-status").value =
    li.dataset.status || "planning";
  bootstrap.Modal.getOrCreateInstance(document.getElementById("edit-plan-modal")).show();
}

function closeEditPlan() {
  bootstrap.Modal.getOrCreateInstance(document.getElementById("edit-plan-modal")).hide();
}

async function savePlanEdit() {
  const name = document.getElementById("edit-plan-name").value.trim();
  const status = document.getElementById("edit-plan-status").value;
  if (!name) return showFeedback("Plan name is required.");
  const res = await fetch(`/garden_planning/api/plans/${editingPlanId}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
    body: JSON.stringify({ name, status }),
  });
  try {
    await readApiResponse(res);
    const li = document.querySelector(
      `#plan-list .plan-item[data-id="${editingPlanId}"]`,
    );
    if (li) {
      li.dataset.status = status;
      li.querySelector(".plan-item-name").textContent = name;
      li.querySelector(".plan-status").outerHTML = planStatusBadge(status);
    }
    closeEditPlan();
  } catch (err) {
    showFeedback(err.message);
  }
}

async function readApiResponse(res) {
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    if (res.redirected && /login/i.test(res.url))
      throw new Error("Your session has expired. Please sign in again.");
    throw new Error(
      `The server returned an unexpected response (HTTP ${res.status}). Reload the page and try again.`,
    );
  }
  let data;
  try {
    data = await res.json();
  } catch (_) {
    throw new Error(
      "The server returned an invalid response. Reload the page and try again.",
    );
  }
  if (!res.ok)
    throw new Error(data.error || `Request failed (HTTP ${res.status}).`);
  return data;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function planStatusInfo(status) {
  const statuses = {
    planning: {
      label: "Planning",
      classes: "bg-secondary-subtle text-secondary-emphasis",
    },
    ready: {
      label: "Ready to plant",
      classes: "bg-warning-subtle text-warning-emphasis",
    },
    planted: {
      label: "Planted",
      classes: "bg-success-subtle text-success-emphasis",
    },
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
        '<li id="empty-plan" class="small text-secondary">No plans yet. Select “+ New plan” to get started.</li>';
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
        <button class="btn btn-outline-success btn-sm" onclick="viewPlan(${Number(plan.id)})">View</button>
        <button class="btn btn-danger btn-sm" onclick="deletePlan(${Number(plan.id)}, this)">Delete</button></div>`;
      list.appendChild(li);
    }
  } catch (err) {
    list.innerHTML = `<li class="text-danger small">${escapeHtml(err.message)}</li>`;
  }
}

async function editPot(id, button) {
  const li = button.closest(".plan-item");
  const name = li.querySelector(".plan-item-name").textContent;
  const oldSize =
    li.querySelector(".plan-item-loc").textContent.match(/^\d+/)?.[0] || "30";
  const values = await showActionModal({
    title: "Edit pot",
    fields: [
      { name: "name", label: "Pot name", value: name },
      { name: "size_cm", label: "Size (cm)", type: "number", min: 1, value: oldSize },
    ],
    submitLabel: "Save changes",
  });
  if (!values) return;
  const size_cm = Number(values.size_cm);
  const res = await fetch(`/garden_planning/api/pots/${id}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
    body: JSON.stringify({ name: values.name.trim(), size_cm }),
  });
  if (!res.ok) return showFeedback("Could not update the pot.");
  htmx.trigger(document.body, "potsChanged");
  showFeedback("Pot updated.", "success");
}

async function deletePot(id, button) {
  const confirmed = await showActionModal({
    title: "Delete pot",
    message: "Are you sure you want to delete this pot?",
    submitLabel: "Delete",
  });
  if (!confirmed) return;
  const res = await fetch(`/garden_planning/api/pots/${id}/`, {
    method: "DELETE",
    headers: { "X-CSRFToken": CSRF },
  });
  if (!res.ok) return showFeedback("Could not delete the pot.");
  htmx.trigger(document.body, "potsChanged");
  showFeedback("Pot deleted.", "success");
}

async function createPlan() {
  const name = document.getElementById("plan-name").value.trim();
  if (!name) return showFeedback("Plan name is required.");

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
  if (!res.ok) return showFeedback(data.error || "Could not create the plan.");

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
      <div class="small text-body-secondary mt-1 plan-item-loc">${escapeHtml(body.location_name || "—")}</div>
    </div>
    <div class="d-flex flex-wrap gap-2">
      <button class="btn btn-outline-success btn-sm" onclick="editPlan(${data.id}, this)">Edit</button>
      <button class="btn btn-outline-success btn-sm" onclick="viewPlan(${Number(data.id)})">View</button>
      <button class="btn btn-danger btn-sm" onclick="deletePlan(${Number(data.id)}, this)">Delete</button>
    </div>
  `;
  document.getElementById("plan-list").appendChild(li);

  document.getElementById("plan-name").value = "";
  document.getElementById("plan-loc").value = "";
  hidePlanForm();
  showFeedback("Plan created.", "success");
}

async function deletePlan(id, btn) {
  const confirmed = await showActionModal({
    title: "Delete plan",
    message: "Are you sure you want to delete this plan?",
    submitLabel: "Delete",
  });
  if (!confirmed) return;
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
        '<li id="empty-plan" class="small text-secondary">No plans yet.</li>';
    }
    showFeedback("Plan deleted.", "success");
  } else {
    showFeedback("Could not delete the plan.");
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
      name: plan.location_name || "Plan location",
    };
    currentProfile = plan.environment_profile || {};
    document.getElementById("refresh-button").disabled = false;
    document.getElementById("city-input").value = currentLocation.name;
    const summary = document.getElementById("weather-summary");
    summary.innerHTML = `<span class="badge rounded-pill text-bg-success">Recommendations for ${escapeHtml(currentLocation.name)}</span>`;
    summary.classList.remove("d-none");
    await fetchRecommendations();
  } catch (error) {
    showFeedback(error.message || "Could not load the plan location.");
  }
}

async function addToPlan(plantId, plantName) {
  const plans = [...document.querySelectorAll("#plan-list .plan-item")];
  if (!plans.length && !targetPlanId) {
    showFeedback("Create a plan before adding a plant.");
    return;
  }

  let planId;
  if (targetPlanId) {
    planId = targetPlanId;
  } else if (plans.length === 1) {
    planId = plans[0].dataset.id;
  } else {
    const selection = await showActionModal({
      title: "Choose a plan",
      message: "Select where to add this plant.",
      submitLabel: "Continue",
      fields: [{
        name: "planId",
        label: "Plan",
        options: plans.map((plan) => ({
          value: plan.dataset.id,
          label: plan.querySelector(".plan-item-name").textContent,
        })),
      }],
    });
    if (!selection) return;
    planId = selection.planId;
  }

  const selectedPlan = plans.find((plan) => plan.dataset.id === String(planId));
  const planLatitude = Number(
    selectedPlan?.dataset.latitude ?? currentLocation.latitude,
  );
  const planLongitude = Number(
    selectedPlan?.dataset.longitude ?? currentLocation.longitude,
  );
  if (
    !Number.isFinite(currentLocation.latitude) ||
    !Number.isFinite(currentLocation.longitude)
  ) {
    return showFeedback("Search for weather before adding a plant.");
  }
  if (
    !Number.isFinite(planLatitude) ||
    !Number.isFinite(planLongitude) ||
    Math.abs(currentLocation.latitude - planLatitude) > 0.01 ||
    Math.abs(currentLocation.longitude - planLongitude) > 0.01
  ) {
    return showFeedback(
      `The recommendation location (${currentLocation.name || "current location"}) does not match this plan's location (${selectedPlan?.querySelector(".plan-item-loc")?.textContent || currentLocation.name || "unknown"}). The plant was not added.`,
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
    showFeedback(`“${plantName}” was added to the plan.`, "success");
  } catch (err) {
    showFeedback(err.message || "Could not add the plant.");
  }
}

function setLoading(id, on) {
  document.getElementById(id).classList.toggle("d-none", !on);
}
loadPlans();
document.getElementById("pot-name-input").placeholder = "Pot name";
document.getElementById("pot-size-input").placeholder = "Size (cm)";
const pageParams = new URLSearchParams(window.location.search);
const requestedPlanId = pageParams.get("plan_id");
if (requestedPlanId) loadPlanForRecommendations(requestedPlanId);
if (pageParams.has("add_pot")) {
  const potInput = document.getElementById("pot-name-input");
  potInput.scrollIntoView({ behavior: "smooth", block: "center" });
  potInput.focus({ preventScroll: true });
}

let refresh = document.getElementById("refresh-button");
refresh.addEventListener("click", fetchRecommendations);
