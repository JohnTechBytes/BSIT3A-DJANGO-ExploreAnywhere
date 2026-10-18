
/* ===========================================
   EXPLOREANYWHERE - CITY SELECTION JAVASCRIPT
   =========================================== */

window.ExploreGeo = (() => {
  const radians = value => value * Math.PI / 180;

  function haversine(aLat, aLng, bLat, bLng) {
    const R = 6371;
    const dLat = radians(bLat - aLat);
    const dLng = radians(bLng - aLng);

    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(radians(aLat)) *
      Math.cos(radians(bLat)) *
      Math.sin(dLng / 2) ** 2;

    return 2 * R * Math.atan2(
      Math.sqrt(Math.min(1, a)),
      Math.sqrt(Math.max(0, 1 - a))
    );
  }

  function findNearest(latitude, longitude, cities) {
    let closest = null;

    for (const city of cities) {
      const lat = Number(city.latitude);
      const lng = Number(city.longitude);

      if (!Number.isFinite(lat) ||
          !Number.isFinite(lng)) continue;

      const distance = haversine(
        latitude, longitude, lat, lng
      );

      if (!closest || distance < closest.distance) {
        closest = { ...city, distance };
      }
    }

    return closest;
  }

  function detect(cities) {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is unavailable."));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        position => {
          const nearest = findNearest(
            position.coords.latitude,
            position.coords.longitude,
            cities
          );
          resolve(nearest);
        },
        reject,
        {
          enableHighAccuracy: false,
          timeout: 12000,
          maximumAge: 60000
        }
      );
    });
  }

  return { haversine, findNearest, detect };
})();

document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const form = document.getElementById(
        "city-selection-form"
    );

    if (!form) return;

    const cityCards = [
        ...document.querySelectorAll(".ea-city-card")
    ];

    const selectedInput = document.getElementById(
        "selected-city-id"
    );

    const continueButton = document.getElementById(
        "continue-city"
    );

    const selectedLabel = document.getElementById(
        "selected-city-label"
    );

    const searchInput = document.getElementById(
        "city-search"
    );

    const noResults = document.getElementById(
        "no-city-results"
    );

    const detectButton = document.getElementById(
        "detect-location"
    );

    const useDetectedButton = document.getElementById(
        "use-detected-city"
    );

    const detectedName = document.getElementById(
        "detected-city-name"
    );

    const locationMessage = document.getElementById(
        "location-message"
    );

    const nearbyBadge = document.getElementById(
        "nearby-badge"
    );

    const cityDataElement = document.getElementById(
        "ea-supported-cities"
    );

    let supportedCities = [];

    if (cityDataElement) {
        try {
            supportedCities = JSON.parse(
                cityDataElement.textContent
            );
        } catch (error) {
            console.error(
                "Invalid supported cities data:",
                error
            );
        }
    }

    let detectedCity = null;

    // ---------------------------------------
    // CITY SELECTION
    // ---------------------------------------

    function selectCity(cityId) {
        let selectedCard = null;

        cityCards.forEach(card => {
            const isSelected =
                !card.disabled &&
                card.dataset.id === String(cityId);

            card.classList.toggle(
                "is-selected",
                isSelected
            );

            card.setAttribute(
                "aria-pressed",
                String(isSelected)
            );

            if (isSelected) {
                selectedCard = card;
            }
        });

        if (!selectedCard) {
            selectedInput.value = "";
            continueButton.disabled = true;

            selectedLabel.textContent =
                "Choose a city to continue";

            return;
        }

        selectedInput.value = selectedCard.dataset.id;
        continueButton.disabled = false;

        const name = selectedCard.dataset.name;
        const province = selectedCard.dataset.province;

        selectedLabel.textContent =
            `Selected: ${name}, ${province}`;
    }

    cityCards.forEach(card => {
        card.addEventListener("click", () => {
            if (!card.disabled) {
                selectCity(card.dataset.id);
            }
        });
    });

    // Restore previously selected city.
    selectCity(selectedInput.value);

    // ---------------------------------------
    // LIVE CITY SEARCH
    // ---------------------------------------

    searchInput.addEventListener("input", () => {
        const searchTerm = searchInput.value
            .trim()
            .toLowerCase();

        let matchingCities = 0;

        cityCards.forEach(card => {
            const cityName = (
                card.dataset.name || ""
            ).toLowerCase();

            const province = (
                card.dataset.province || ""
            ).toLowerCase();

            const matches =
                cityName.includes(searchTerm) ||
                province.includes(searchTerm);

            card.hidden = !matches;

            if (matches) {
                matchingCities++;
            }
        });

        noResults.hidden =
            matchingCities !== 0 ||
            searchTerm === "";
    });

    // ---------------------------------------
    // HAVERSINE DISTANCE
    // ---------------------------------------

    function haversineDistance(
        latitude1,
        longitude1,
        latitude2,
        longitude2
    ) {
        const earthRadiusKm = 6371;

        const toRadians = degrees =>
            degrees * Math.PI / 180;

        const deltaLatitude = toRadians(
            latitude2 - latitude1
        );

        const deltaLongitude = toRadians(
            longitude2 - longitude1
        );

        const a =
            Math.sin(deltaLatitude / 2) ** 2 +
            Math.cos(toRadians(latitude1)) *
            Math.cos(toRadians(latitude2)) *
            Math.sin(deltaLongitude / 2) ** 2;

        const safeA = Math.min(
            1,
            Math.max(0, a)
        );

        const c = 2 * Math.atan2(
            Math.sqrt(safeA),
            Math.sqrt(1 - safeA)
        );

        return earthRadiusKm * c;
    }

    // ---------------------------------------
    // FIND NEAREST SUPPORTED CITY
    // ---------------------------------------

    function findNearestCity(latitude, longitude) {
        let nearest = null;

        supportedCities.forEach(city => {
            const cityLatitude = Number(
                city.latitude
            );

            const cityLongitude = Number(
                city.longitude
            );

            if (
                !Number.isFinite(cityLatitude) ||
                !Number.isFinite(cityLongitude)
            ) {
                return;
            }

            const distance = haversineDistance(
                latitude,
                longitude,
                cityLatitude,
                cityLongitude
            );

            if (
                nearest === null ||
                distance < nearest.distance
            ) {
                nearest = {
                    ...city,
                    distance: distance
                };
            }
        });

        return nearest;
    }

    // ---------------------------------------
    // DETECT LOCATION
    // ---------------------------------------

    detectButton.addEventListener("click", () => {
        nearbyBadge.hidden = true;
        useDetectedButton.hidden = true;
        detectedCity = null;

        if (!navigator.geolocation) {
            locationMessage.textContent =
                "Your browser does not support location detection.";
            return;
        }

        if (!supportedCities.length) {
            locationMessage.textContent =
                "No active cities with coordinates are available.";
            return;
        }

        detectButton.disabled = true;

        locationMessage.textContent =
            "Finding your nearest supported city...";

        navigator.geolocation.getCurrentPosition(
            position => {
                detectButton.disabled = false;

                const latitude =
                    position.coords.latitude;

                const longitude =
                    position.coords.longitude;

                const nearest = findNearestCity(
                    latitude,
                    longitude
                );

                if (!nearest) {
                    locationMessage.textContent =
                        "No supported city could be detected.";
                    return;
                }

                detectedCity = nearest;

                detectedName.textContent =
                    `${nearest.name}, ${nearest.province}`;

                const distanceText =
                    nearest.distance.toFixed(1);

                locationMessage.textContent =
                    `${distanceText} km from the recorded city center`;

                // Nearby is shown only when genuinely
                // close to the stored city center.
                nearbyBadge.hidden =
                    nearest.distance > 50;

                useDetectedButton.hidden = false;
            },
            error => {
                detectButton.disabled = false;

                if (error.code === 1) {
                    locationMessage.textContent =
                        "Location permission denied. You can select a city manually.";
                } else if (error.code === 2) {
                    locationMessage.textContent =
                        "Your location is currently unavailable.";
                } else {
                    locationMessage.textContent =
                        "Location detection timed out. Please try again.";
                }
            },
            {
                enableHighAccuracy: false,
                timeout: 12000,
                maximumAge: 60000
            }
        );
    });

    // ---------------------------------------
    // USE DETECTED CITY
    // ---------------------------------------

    useDetectedButton.addEventListener("click", () => {
        if (!detectedCity) return;

        selectCity(detectedCity.id);

        if (selectedInput.value) {
            form.requestSubmit();
        }
    });

    // ---------------------------------------
    // PREVENT EMPTY SUBMISSION
    // ---------------------------------------

    form.addEventListener("submit", event => {
        if (!selectedInput.value) {
            event.preventDefault();

            selectedLabel.textContent =
                "Please select an active city first.";
        }
    });
});
