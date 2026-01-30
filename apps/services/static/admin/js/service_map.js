(function () {
  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  function parseNumber(value) {
    var num = parseFloat(value);
    return Number.isFinite(num) ? num : null;
  }

  ready(function () {
    var latInput = document.getElementById("id_latitude");
    var lngInput = document.getElementById("id_longitude");
    if (!latInput || !lngInput || !window.L) {
      return;
    }

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "button";
    btn.textContent = "Select on map";

    var lngRow = lngInput.closest(".form-row") || lngInput.parentElement;
    if (lngRow) {
      lngRow.appendChild(btn);
    }

    var modal = document.createElement("div");
    modal.className = "service-map-modal";
    modal.innerHTML = [
      '<div class="service-map-dialog">',
      '  <div class="service-map-header">',
      "    <span>Select location</span>",
      '    <button type="button" class="button" data-close="1">Close</button>',
      "  </div>",
      '  <div class="service-map-body"><div id="service-map"></div></div>',
      '  <div class="service-map-footer">',
      '    <button type="button" class="button default" data-use="1">Use</button>',
      "  </div>",
      "</div>",
    ].join("");
    document.body.appendChild(modal);

    var map;
    var marker;

    function getLatLngFromInputs() {
      var lat = parseNumber(latInput.value);
      var lng = parseNumber(lngInput.value);
      if (lat === null || lng === null) {
        return null;
      }
      return { lat: lat, lng: lng };
    }

    function setInputs(lat, lng) {
      latInput.value = lat.toFixed(6);
      lngInput.value = lng.toFixed(6);
    }

    var pendingLatLng = null;

    function initMap() {
      var initial = getLatLngFromInputs() || { lat: 38.0, lng: 58.3 };
      var zoom = getLatLngFromInputs() ? 14 : 6;
      map = L.map("service-map").setView([initial.lat, initial.lng], zoom);
      L.tileLayer(window.SERVICE_MAP_TILE_URL || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(map);
      marker = L.marker([initial.lat, initial.lng], { draggable: true }).addTo(map);
      pendingLatLng = { lat: initial.lat, lng: initial.lng };
      marker.on("dragend", function () {
        var pos = marker.getLatLng();
        pendingLatLng = { lat: pos.lat, lng: pos.lng };
      });
      map.on("click", function (e) {
        marker.setLatLng(e.latlng);
        pendingLatLng = { lat: e.latlng.lat, lng: e.latlng.lng };
      });
    }

    function syncMarker() {
      if (!map || !marker) {
        return;
      }
      var pos = getLatLngFromInputs();
      if (!pos) {
        return;
      }
      marker.setLatLng([pos.lat, pos.lng]);
      map.setView([pos.lat, pos.lng], 14);
      pendingLatLng = { lat: pos.lat, lng: pos.lng };
    }

    function openModal() {
      modal.classList.add("is-open");
      if (!map) {
        initMap();
      } else {
        map.invalidateSize();
        syncMarker();
      }
    }

    function closeModal() {
      modal.classList.remove("is-open");
    }

    btn.addEventListener("click", openModal);
    modal.querySelector("[data-close]").addEventListener("click", closeModal);
    modal.querySelector("[data-use]").addEventListener("click", function () {
      if (pendingLatLng) {
        setInputs(pendingLatLng.lat, pendingLatLng.lng);
      }
      closeModal();
    });
    modal.addEventListener("click", function (e) {
      if (e.target === modal) {
        closeModal();
      }
    });
  });
})();
