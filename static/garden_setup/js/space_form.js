
document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("gs-form-root");
    const form = document.getElementById("gs-space-form");

    if (!root || !form) return;

    const cityInput = document.getElementById("id_city");
    const suggestions = document.getElementById("gs-location-results");
    const status = document.getElementById("gs-location-status");
    const summary = document.getElementById("gs-location-summary");

    const searchUrl = root.dataset.searchUrl;

    const locationFields = [
        "geocoding_id",
        "region",
        "country",
        "latitude",
        "longitude",
        "timezone"
    ];

    let debounceTimer;
    let activeController = null;
    let requestVersion = 0;

    function getField(name) {
        return form.elements.namedItem(name);
    }

    function getValue(name) {
        return getField(name)?.value || "";
    }

    function selectedLabel(name) {
        const radio = form.querySelector(
            `input[name="${name}"]:checked`
        );

        if (radio) {
            return radio.closest("label")
                ?.querySelector("span")
                ?.textContent.trim() || "—";
        }

        const field = getField(name);

        if (field?.tagName === "SELECT") {
            const option = field.selectedOptions[0];

            if (option?.value) {
                return option.textContent.trim();
            }
        }

        return "—";
    }

    function setText(id, value) {
        const element = document.getElementById(id);

        if (element) {
            element.textContent = value || "—";
        }
    }

    function updatePreview() {
        setText(
            "gs-preview-name",
            getValue("name").trim() || "Your Growing Space"
        );

        setText(
            "gs-preview-location",
            getValue("city").trim() || "Location not selected"
        );

        setText(
            "gs-preview-environment",
            selectedLabel("environment")
        );

        const selectedSpaceType = getValue("space_type");
        const specifiedType = getValue("other_space_type").trim();

        setText(
            "gs-preview-type",
            selectedSpaceType === "other"
                ? (specifiedType || "Other")
                : selectedLabel("space_type")
        );

        setText(
            "gs-preview-sunlight",
            selectedLabel("sunlight_range")
        );

        setText(
            "gs-preview-medium",
            selectedLabel("growing_medium")
        );

        setText(
            "gs-preview-pots",
            getValue("pot_capacity")
                ? `${getValue("pot_capacity")} pots`
                : "—"
        );

        setText(
            "gs-preview-care",
            selectedLabel("care_availability")
        );
    }

    function closeSuggestions() {
        suggestions.hidden = true;
        suggestions.replaceChildren();
    }

    function clearLocation() {
        for (const name of locationFields) {
            const field = getField(name);

            if (field) {
                field.value = "";
            }
        }

        summary.textContent = "Not selected";
    }

    function cancelSearch() {
        clearTimeout(debounceTimer);
        requestVersion += 1;

        if (activeController) {
            activeController.abort();
            activeController = null;
        }
    }

    function chooseLocation(location) {
        cancelSearch();

        const values = {
            geocoding_id: location.id,
            region: location.region || "",
            country: location.country,
            latitude: location.latitude,
            longitude: location.longitude,
            timezone: location.timezone
        };

        for (const [name, value] of Object.entries(values)) {
            const field = getField(name);

            if (field) {
                field.value = value;
            }
        }

        cityInput.value = location.name;

        const description = [
            location.name,
            location.region,
            location.country
        ].filter(Boolean).join(", ");

        summary.textContent = description;
        status.textContent = `Selected: ${description}`;

        closeSuggestions();
        updatePreview();
        cityInput.focus();
    }

    function showSuggestions(locations) {
        closeSuggestions();

        if (locations.length === 0) {
            status.textContent = "No matching locations found.";
            return;
        }

        for (const location of locations) {
            const button = document.createElement("button");

            button.type = "button";
            button.className = "gs-location-choice";

            button.textContent = [
                location.name,
                location.region,
                location.country
            ].filter(Boolean).join(", ");

            button.addEventListener("click", () => {
                chooseLocation(location);
            });

            suggestions.appendChild(button);
        }

        suggestions.hidden = false;
        status.textContent =
            "Select a location from the suggestions.";
    }

    async function searchCity(query, version) {
        const controller = new AbortController();
        activeController = controller;

        const url = new URL(
            searchUrl,
            window.location.origin
        );

        url.searchParams.set("q", query);
        status.textContent = "Searching locations...";

        try {
            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    "Accept": "application/json"
                }
            });

            const data = await response.json();

            if (version !== requestVersion) return;

            if (!response.ok) {
                throw new Error(
                    data.error || "Location search failed."
                );
            }

            showSuggestions(data.results || []);

        } catch (error) {
            if (version !== requestVersion) return;
            if (error.name === "AbortError") return;

            closeSuggestions();
            status.textContent =
                error.message || "Location service unavailable.";

        } finally {
            if (activeController === controller) {
                activeController = null;
            }
        }
    }

    if (cityInput && suggestions && status && summary) {
        cityInput.setAttribute("autocomplete", "off");

        cityInput.addEventListener("input", () => {
            cancelSearch();
            clearLocation();
            closeSuggestions();
            updatePreview();

            const query = cityInput.value.trim();

            if (query.length < 2) {
                status.textContent =
                    "Type at least 2 characters to search.";
                return;
            }

            const version = requestVersion;

            debounceTimer = setTimeout(() => {
                searchCity(query, version);
            }, 350);
        });

        cityInput.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeSuggestions();
            }

            if (event.key === "ArrowDown" && !suggestions.hidden) {
                const first = suggestions.querySelector("button");

                if (first) {
                    event.preventDefault();
                    first.focus();
                }
            }
        });

        suggestions.addEventListener("keydown", (event) => {
            const buttons = Array.from(
                suggestions.querySelectorAll("button")
            );

            const index = buttons.indexOf(document.activeElement);

            if (event.key === "Escape") {
                closeSuggestions();
                cityInput.focus();
            } else if (event.key === "ArrowDown") {
                event.preventDefault();
                buttons[Math.min(index + 1, buttons.length - 1)]
                    ?.focus();
            } else if (event.key === "ArrowUp") {
                event.preventDefault();

                if (index <= 0) {
                    cityInput.focus();
                } else {
                    buttons[index - 1]?.focus();
                }
            }
        });

        document.addEventListener("click", (event) => {
            if (!event.target.closest(".gs-location-wrapper")) {
                closeSuggestions();
            }
        });

        if (getValue("geocoding_id") && cityInput.value) {
            summary.textContent = [
                getValue("city"),
                getValue("region"),
                getValue("country")
            ].filter(Boolean).join(", ");

            status.textContent = "Current location selected.";
        }

        form.addEventListener("submit", (event) => {
            if (!getValue("geocoding_id")) {
                event.preventDefault();

                status.textContent =
                    "Please select a city from the suggestions.";

                cityInput.focus();
            }
        });
    }

    const rainField = getField("rain_access");

    form.addEventListener("change", (event) => {
        if (event.target.name === "environment") {
            if (
                selectedLabel("environment")
                    .toLowerCase() === "indoor"
                && rainField
            ) {
                rainField.value = "sheltered";
            }
        }

        updatePreview();
    });

    form.addEventListener("input", updatePreview);

    // Tampilkan input tambahan hanya saat Space Type = Other.
    const spaceTypeSelect = form.elements.namedItem("space_type");
    const otherTypeWrapper = document.getElementById(
        "gs-other-type-wrapper"
    );
    const otherTypeInput = form.elements.namedItem(
        "other_space_type"
    );

    function toggleOtherSpaceType() {
        if (
            !spaceTypeSelect ||
            !otherTypeWrapper ||
            !otherTypeInput
        ) {
            return;
        }

        const isOther = spaceTypeSelect.value === "other";

        otherTypeWrapper.hidden = !isOther;
        otherTypeInput.required = isOther;

        if (!isOther) {
            otherTypeInput.value = "";
        }
    }

    if (spaceTypeSelect && otherTypeWrapper && otherTypeInput) {
        spaceTypeSelect.addEventListener("change", () => {
            toggleOtherSpaceType();
            updatePreview();
        });

        toggleOtherSpaceType();
    }

    updatePreview();
});
