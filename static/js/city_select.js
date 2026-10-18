
document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const cfg = window.exploreCityConfig;
  if (!cfg) return;

  const $ = id => document.getElementById(id);

  const provinceSelect = $("province-select");
  const search = $("city-search");
  const grid = $("city-grid");
  const hint = $("city-hint");
  const empty = $("city-empty");
  const count = $("city-count");
  const status = $("city-status");
  const more = $("load-more");
  const chosenInput = $("city-id");
  const chosenLabel = $("selected-city-label");
  const submit = $("continue-to-hobbies");
  const addCity = $("admin-add-city");

  let page = 1;
  let loading = false;
  let queryVersion = 0;
  let searchTimer = null;
  let selectedCity = null;

  const selectedId = Number(cfg.selectedCityId) || null;

  function svgIcon(type) {
    if (type === "check") {
      return `<svg viewBox="0 0 24 24"
        fill="none" stroke="currentColor"
        stroke-width="2" aria-hidden="true">
        <path d="m5 12 4 4L19 6"/></svg>`;
    }

    return `<svg viewBox="0 0 24 24"
      fill="none" stroke="currentColor"
      stroke-width="2" aria-hidden="true">
      <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/>
      <circle cx="12" cy="10" r="2.5"/>
    </svg>`;
  }

  function setSelected(city) {
    selectedCity = city;
    chosenInput.value = city ? city.id : "";
    submit.disabled = !city;

    chosenLabel.textContent = city
      ? `Selected: ${city.name}, ${city.province}`
      : "Choose a city to continue";

    grid.querySelectorAll(".select-city-card").forEach(card => {
      const active = Boolean(
        city && Number(card.dataset.id) === Number(city.id)
      );

      card.classList.toggle("selected", active);
      card.setAttribute("aria-pressed", String(active));
    });
  }

  
function createCard(city) {
    const button = document.createElement("button");

    button.type = "button";
    button.className = "select-city-card";
    button.dataset.id = String(city.id);

    // Pending means attractions have not been
    // added yet. It does NOT disable city selection.
    const hasPlaces = city.active === true;

    if (!hasPlaces) {
        button.classList.add("pending");
    }

    const top = document.createElement("div");
    top.className = "select-card-top";

    const icon = document.createElement("span");
    icon.className = "select-card-icon";
    icon.innerHTML = svgIcon("pin");

    const check = document.createElement("span");
    check.className = "select-check";
    check.innerHTML = svgIcon("check");

    top.append(icon, check);

    const name = document.createElement("h3");
    name.textContent = city.name;

    const location = document.createElement("p");
    location.className = "select-card-location";
    location.textContent =
        `${city.province}, ${city.region}`;

    const bottom = document.createElement("div");
    bottom.className = "select-card-bottom";

    const badge = document.createElement("span");
    badge.className = hasPlaces
        ? "status-badge active"
        : "status-badge pending";

    badge.textContent = hasPlaces
        ? "Active"
        : "No places yet";

    const places = document.createElement("span");
    places.className = "place-number";

    places.textContent =
        `${city.places_count} places available`;

    bottom.append(badge, places);
    button.append(top, name, location, bottom);

    // Every city or municipality is selectable.
    button.addEventListener("click", () => {
        setSelected(city);
    });

    return button;
}

async function loadProvinces() {
    const response = await fetch(cfg.provincesUrl);

    if (!response.ok) {
      throw new Error("Unable to load provinces.");
    }

    const data = await response.json();
    const groups = new Map();

    for (const province of data.provinces) {
      if (!groups.has(province.region)) {
        groups.set(province.region, []);
      }
      groups.get(province.region).push(province);
    }

    for (const [region, provinces] of groups) {
      const group = document.createElement("optgroup");
      group.label = region;

      for (const province of provinces) {
        const option = document.createElement("option");
        option.value = province.slug;
        option.textContent = province.name;
        group.append(option);
      }

      provinceSelect.append(group);
    }
  }

  async function fetchCities(reset = false) {
    const province = provinceSelect.value;

    if (!province) {
      grid.replaceChildren();
      grid.hidden = true;
      hint.hidden = false;
      empty.hidden = true;
      more.hidden = true;
      count.textContent = "";
      search.disabled = true;
      if (addCity) addCity.hidden = true;
      return;
    }

    if (loading && !reset) return;

    const currentVersion = ++queryVersion;
    const requestedPage = reset ? 1 : page;
    loading = true;

    if (reset) {
      grid.replaceChildren();
      page = 1;
      setSelected(null);
    }

    search.disabled = false;
    hint.hidden = true;
    grid.hidden = false;
    empty.hidden = true;
    more.hidden = true;
    status.textContent = "Loading cities...";

    const params = new URLSearchParams({
      province,
      q: search.value.trim(),
      page: String(requestedPage),
    });

    try {
      const response = await fetch(
        `${cfg.citiesUrl}?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error("Unable to load cities.");
      }

      const data = await response.json();

      if (currentVersion !== queryVersion) return;

      const fragment = document.createDocumentFragment();

      data.cities.forEach(city => {
        fragment.appendChild(createCard(city));
      });

      grid.appendChild(fragment);

      count.textContent =
        `Showing ${grid.querySelectorAll(".select-city-card").length} ` +
        `of ${data.total} cities`;

      status.textContent = "";

      empty.textContent =
        `No cities found in ${data.province}. ` +
        "Try another search.";

      empty.hidden = data.total !== 0;

      page = requestedPage + 1;
      more.hidden = !data.has_next;

      if (addCity) addCity.hidden = false;

      if (selectedCity) {
        setSelected(selectedCity);
      }
    } catch (error) {
      if (currentVersion === queryVersion) {
        status.textContent =
          "Could not load cities. Please try again.";
      }
    } finally {
      if (currentVersion === queryVersion) {
        loading = false;
      }
    }
  }

  provinceSelect.addEventListener("change", () => {
    search.value = "";
    setSelected(null);
    fetchCities(true);
  });

  search.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(
      () => fetchCities(true),
      250
    );
  });

  more.addEventListener("click", () => {
    fetchCities(false);
  });

  // Geolocation: only request permission on click.
  const detectButton = $("detect-location");
  const detectedRow = $("detected-row");
  const useDetected = $("use-detected-city");
  const detectedName = $("detected-name");

  let nearestCity = null;

  if (detectButton) {
    detectButton.addEventListener("click", async () => {
      let candidates = [];

      try {
        candidates = JSON.parse(
          $("geolocation-cities").textContent
        );
      } catch {
        return;
      }

      detectButton.disabled = true;

      try {
        nearestCity = await window.ExploreGeo.detect(
          candidates
        );

        if (nearestCity) {
          detectedName.textContent =
            `${nearestCity.name}, ` +
            nearestCity.province_name;

          detectedRow.hidden = false;
        }
      } catch {
        detectedRow.hidden = true;
      } finally {
        detectButton.disabled = false;
      }
    });
  }

  if (useDetected) {
    useDetected.addEventListener("click", async () => {
      if (!nearestCity) return;

      provinceSelect.value = nearestCity.province_slug;
      search.value = "";
      await fetchCities(true);

      // A detected city may be beyond the first
      // 24 results; fetch the exact city by searching.
      search.value = nearestCity.name;
      await fetchCities(true);

      const card = [...grid.querySelectorAll(".select-city-card")]
        .find(c => Number(c.dataset.id) === nearestCity.id);

      if (card && !card.disabled) {
        card.click();
      }
    });
  }

  async function initialize() {
    try {
      await loadProvinces();

      if (cfg.selectedProvince) {
        provinceSelect.value = cfg.selectedProvince;
        await fetchCities(true);
      }
    } catch (error) {
      status.textContent = error.message;
    }
  }

  initialize();
});
