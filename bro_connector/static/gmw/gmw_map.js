// Get information
const wells = JSON.parse(document.getElementById("wells_json").textContent);
const gmns = JSON.parse(document.getElementById("gmns_json").textContent);
const organisations = JSON.parse(
  document.getElementById("organisations_json").textContent
);
const glds = JSON.parse(
  document.getElementById("groundwater_level_dossiers_json").textContent
);
const wellMap = Object.fromEntries(
  wells.map((well) => [well.groundwater_monitoring_well_static_id + "", well])
);

// Visible mapping
const visibleMap = {
  gmns: {
    noLinked: true,
  },
  organisations: {},
  wellValue: {},
};

gmns.forEach((gmn) => {
  visibleMap.gmns[gmn] = true;
});

const colorMap = {};

const hexToRgb = (hex) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b, 200];
};

// Add color and visible map for each organisation
Object.keys(organisations).forEach((orgKey) => {
  const { color, id } = organisations[orgKey];

  // Apply color to html checkbox
  const organisationCheckbox = document.getElementById(`checkbox-${id}`);
  organisationCheckbox.style.accentColor = color;
  organisationCheckbox.style.background = color;

  // Add color to color map
  const rgbColor = hexToRgb(color);
  colorMap[id] = rgbColor;
  visibleMap.organisations[id] = true;
});

// Show check or cross
const checkOrCross = (boolean) => (boolean ? "&check;" : "&cross;");

// Create a popup with well information and a link to the object page
const createPopup = (well) => {
  const popup = document.createElement("div");
  const objectPageUrl = `/admin/gmw/groundwatermonitoringwellstatic/${well.groundwater_monitoring_well_static_id}`;
  const BROloketUrl = `https://www.broloket.nl/ondergrondgegevens?bro-id=${well.bro_id}`;
  const gldPageUrl = `/admin/gld/groundwaterleveldossier/?q=${well.bro_id}`;
  const frdPageUrl = `/admin/frd/formationresistancedossier/?q=${well.bro_id}`;
  const popupContent = `
              <div id="popup-content">
                <a href="${objectPageUrl}" target="_blank"><strong style="font-size: 18px;">${well.well_code
    }</strong></a>
                <hr width="100%" size="2">
                <div class="well-item">
                  <span class="label">BRO-ID:</span>
                  <span class="value">${well.bro_id}</span>
                </div>
                <div class="well-item">
                  <span class="label">NITG-code:</span>
                  <span class="value">${well.nitg_code}</span>
                </div>
                <div class="well-item">
                  <span class="label">GMW naar BRO:</span>
                  <span class="value">${checkOrCross(
      well.deliver_gmw_to_bro
    )}</span>
                </div>
                <div class="well-item">
                  <span class="label">BRO compleet:</span>
                  <span class="value">${checkOrCross(well.complete_bro)}</span>
                </div>
                <div class="well-item">
                  <span class="label">In beheer:</span>
                  <span class="value">${checkOrCross(well.in_management)}</span>
                </div>
                <div class="well-item">
                  <span class="label">BRO-loket:</span>
                  <span class="value"><a href="${BROloketUrl}" target="_blank">broloket link</a></span>
                </div>
                <div class="well-item">
                  <span class="label">GMNs:</span>
                  <span class="value">${well.linked_gmns}</span>
                </div>
                <div class="well-item">
                  <span class="label">Zoek GLDs: </span>
                  <span class="value"><a href="${gldPageUrl}" target="_blank">GLDs</a></span>
                </div>
                <div class="well-item">
                  <span class="label">Zoek FRDs: </span>
                  <span class="value"><a href="${frdPageUrl}" target="_blank">FRDs</a></span>
                </div>
                <div class="well-item">
                  <span class="label">Foto: </span>
                  <span class="value">${well.picture}</span>
                </div>
              </div>
              <div style="display: flex; width: 100%; justify-content: center; padding-bottom: 0.5em;">
                <div style="clip-path: polygon(100% 0, 0 0, 50% 100%); width: 10px; height: 10px; background-color: white;"></div>
              </div>
                  `;
  popup.innerHTML = popupContent;
  return popup;
};

const showWellPopupAndMove = (well) => {
  if (marker) marker.remove();
  const popup = createPopup(well);
  const lngLat = [well.y, well.x];

  const newMarker = new mapboxgl.Marker(popup, { anchor: "top", offset: [-150, -200] })
    .setLngLat(lngLat)
    .addTo(map);
  setTimeout(() => (marker = newMarker));

  map.flyTo({ center: lngLat, zoom: 15, essential: true });
};

const wellIsShown = (well) => {
  // Hide if doenst have linked_gmns and notLinked is false or if visibileMap doesnt have any of the linked gmns
  if (
    (well.linked_gmns.length === 0 && !visibleMap.gmns.noLinked) ||
    (well.linked_gmns.length &&
      !well.linked_gmns.find((gmn) => visibleMap.gmns[gmn]))
  )
    return;

  // Hide if organisation is hidden
  if (!visibleMap.organisations[well.delivery_accountable_party]) return;

  // Hide if one of the wellvalues is set to hidden
  const wellValueKeys = Object.keys(visibleMap.wellValue);
  if (
    wellValueKeys.find(
      (valueKey) =>
        (visibleMap.wellValue[valueKey] === true && !well[valueKey]) ||
        (visibleMap.wellValue[valueKey] === false && well[valueKey])
    )
  )
    return;
  return true;
};

const WHITE = [255, 255, 255];
const BLACK = [0, 0, 0];
let marker = null;

// For each well, add a circle
const myScatterplotLayer = new deck.MapboxLayer({
  id: "scatterplot-layer",
  data: wells,
  type: deck.ScatterplotLayer,
  getPosition: (well) => [well.y, well.x],
  pickable: true,
  radiusMaxPixels: 6.5,
  radiusUnits: "meters",
  lineWidthMaxPixels: 1,
  lineWidthUnits: "meters",
  getLineWidth: 0.005,
  stroked: true,
  filled: true,
  antialiasing: true,
  radiusUnits: "pixels",
  getFillColor: (well) => colorMap[well.delivery_accountable_party],
  lineWidthMinPixels: 2,
  getLineColor: WHITE,

  // Hide circle when gmn or organisation is set to invisible
  getRadius: (well) => (wellIsShown(well) ? 10 : 0),

  //   On click add a popup as an Mapbox marker at the circle's location
  onClick: (event) => {
    const well = event.object;
    showWellPopupAndMove(well);
  },
});

function filterByCheckbox(wellValue, checkboxId) {
  const checkbox = document.getElementById(`checkbox-${checkboxId}`);
  if (!checkbox) return true; // Default to show if checkbox missing

  const checked = checkbox.checked;
  const indeterminate = checkbox.indeterminate;

  if (wellValue === true) {
    // true wells show if checkbox is checked or indeterminate
    return checked || indeterminate;
  } else {
    // false wells show if checkbox is unchecked or indeterminate
    return !checked || indeterminate;
  }
}

function createTextLayer(visible) {
  const visibleWells = wells.filter(well => {
    // Filter based on wellValue checkboxes:
    if (!filterByCheckbox(well.complete_bro, 'complete_bro')) return false;
    if (!filterByCheckbox(well.has_open_comments, 'open_comments')) return false;
    if (!filterByCheckbox(well.deliver_gmw_to_bro, 'deliver_gmw_to_bro')) return false;

    // Filter based on linked_gmns & noLinked checkbox
    if (!well.linked_gmns || well.linked_gmns.length === 0) {
      if (visibleMap.gmns.noLinked !== true) {
        return false; // noLinked is off, exclude wells without GMNs
      }
    } else if (!well.linked_gmns.some(gmn => visibleMap.gmns[gmn] === true)) {
      return false; // none of linked GMNs enabled, exclude well
    }

    // Filter based on organisations delivery_accountable_party
    if (
      well.delivery_accountable_party && // only check if attribute present
      visibleMap.organisations[well.delivery_accountable_party] === false
    ) {
      return false; // delivery accountable party is off, exclude well
    }

    // Passed all filters, include the well
    return true;
  });

  return new deck.MapboxLayer({
    id: "text-layer",
    data: visibleWells,
    type: deck.TextLayer,
    getPosition: (well) => [well.y, well.x],
    getText: (well) => well.label + "",
    getAlignmentBaseline: "bottom",
    getColor: BLACK,
    getSize: 100,
    sizeUnits: "meters",
    sizeMaxPixels: 15,
    getPixelOffset: [50, -30],
    getTextAnchor: "middle",
    getAngle: 30,
    visible: visible,
  });
}

function updateTextLayer() {
  if (map.getLayer("text-layer")) {
    map.removeLayer("text-layer"); // remove old layer
  }

  visible = isTextLayerVisible && shouldShowText
  textLayer = createTextLayer(visible); // create new layer with updated filtering
  map.addLayer(textLayer); // add to your deck/map instance
};

// Create the map
const map = new mapboxgl.Map({
  container: "deck-gl-canvas",
  style: {
    version: 8,
    sources: {
      "raster-tiles": {
        type: "raster",
        tiles: [
          "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/water/EPSG:3857/{z}/{x}/{y}.png",
        ],
        tileSize: 256,
        attribution:
          'Kaartgegevens &copy; <a href="https://www.kadaster.nl">Kadaster</a>',
      },
    },
    layers: [
      {
        id: "simple-tiles",
        type: "raster",
        source: "raster-tiles",
        minzoom: 6,
        maxzoom: 19,
      },
    ],
  },
  antialias: true,
  center: [3.945697, 51.522601],
  zoom: 9,
  bearing: 0,
  pitch: 0,
});

// Add map control and circle layer
map.addControl(new mapboxgl.NavigationControl(), "bottom-left");
map.on("load", () => {
  map.addLayer(myScatterplotLayer);
});


map.on("zoom", () => {
  const zoom = map.getZoom();
  shouldShowText = zoom >= 12;
  // Remove the old layer if it exists
  if (map.getLayer("text-layer")) {
    map.removeLayer("text-layer");
  }
  // Add it back with correct visibility
  if (shouldShowText && isTextLayerVisible) {
    // const newTextLayer = createTextLayer(true);
    // map.addLayer(newTextLayer);
    updateTextLayer()
  }
});

// Remove popup on map click
map.on("click", () => marker && marker.remove());

// Get the toggle button element
const toggleTextLayerButton = document.getElementById("toggle-text-layer-btn");

// Variable to keep track of the layer's visibility state
let isTextLayerVisible = false;
let shouldShowText = false;
// Function to toggle the visibility of the text layer
const toggleTextLayerVisibility = () => {
  const zoom = map.getZoom();
  shouldShowText = zoom >= 12;
  
  try {
    isTextLayerVisible = !isTextLayerVisible;
    updateTextLayer()
  } catch (error) {
    console.error("Error toggling the text layer visibility:", error);
  }
};

// Attach the toggle function to the button click event
toggleTextLayerButton.addEventListener("click", toggleTextLayerVisibility);

// Set the cursor style
const mapCanvas = map.getCanvas();
let cursor = "pointer";
const setCursorStyle = (style) => {
  cursor = style;
  mapCanvas.classList.remove("grab");
  mapCanvas.classList.remove("pointer");
  mapCanvas.classList.remove("grabbing");
  mapCanvas.classList.add(cursor);
};

// Event listeners for the cursor styles
map.on("dragstart", () => setCursorStyle("grabbing"));
map.on("dragend", () => setCursorStyle("grab"));
map.on("mousemove", (e) => {
  const isHovering = e.target.__deck && e.target.__deck.cursorState.isHovering;
  if (isHovering && cursor === "grab") return setCursorStyle("pointer");
  if (!isHovering && cursor === "pointer") return setCursorStyle("grab");
});

// Handle if someone toggles any other filter
const handleWellValue = (id, element) => {
  const checkbox = element.querySelector('input[type="checkbox"]');
  const { wellValue } = visibleMap;
  // Well value can either be false, true or null
  if (wellValue[id] === false) {
    wellValue[id] = null;
    checkbox.checked = false;
    checkbox.indeterminate = true;
  } else if (wellValue[id] === true) {
    wellValue[id] = false;
    checkbox.checked = false;
    checkbox.indeterminate = false;
  } else {
    wellValue[id] = true;
    checkbox.checked = true;
    checkbox.indeterminate = false;
  }
  updateGetRadius();
  updateTextLayer();
};

const deselectAllCheckboxes = () => {
  if (!visibleMap || !visibleMap.gmns) {
    console.warn("❌ visibleMap.gmns not defined");
    return;
  }

  const gmns = visibleMap.gmns;
  console.log("🔍 Current visibleMap.gmns state:", gmns);

  // Check if any GMN is false
  const anyFalse = Object.values(gmns).some(value => value === false);
  console.log(`❓ Any GMN false? ${anyFalse}`);

  // Decide the new state: if any false => set all true; else set all false
  const newState = anyFalse ? true : false;
  console.log(`➡️ Setting all GMNs to: ${newState}`);

  // Update visibleMap.gmns
  Object.keys(gmns).forEach(key => {
    gmns[key] = newState;
  });

  // Sync checkboxes with visibleMap.gmns state
  Object.keys(gmns).forEach(key => {
    let searchKey = key === "noLinked" ? "no-linked" : key;
    const escapedKey = CSS.escape(searchKey);
    const checkbox = document.querySelector(`#checkbox-${escapedKey}`);
    if (checkbox) {
      checkbox.checked = newState;
      console.log(`✔️ Checkbox for '${searchKey}' set to ${newState}`);
    } else {
      console.warn(`⚠️ Checkbox #checkbox-${searchKey} not found in DOM`);
    }
  });

  updateGetRadius();
  updateTextLayer();
};


// Handle if someone toggles an gmn
const handleGmnClick = (id, element) => {
  const checkbox = element.querySelector('input[type="checkbox"]');
  const { gmns } = visibleMap;
  gmns[id] = !gmns[id];
  checkbox.checked = gmns[id];
  updateGetRadius();
  updateTextLayer();
};

// Handle if someone toggles an organisation
const handleOrganisationClick = (id, element) => {
  const checkbox = element.querySelector('input[type="checkbox"]');
  const { organisations } = visibleMap;
  organisations[id] = !organisations[id];
  checkbox.checked = organisations[id];
  updateGetRadius();
  updateTextLayer();
};

const updateGetRadius = () => {
  //   Updating the update triggers to Date.now() makes sure the getRadius gets recaluclated
  myScatterplotLayer.setProps({
    updateTriggers: {
      getRadius: Date.now(),
    },
  });
};

// Clicking the checkbox needs to switch the checkbox back because the above functions handle that
const handleWellValueCheckboxClick = (checkbox) => {
  setTimeout(() => {
    if (!checkbox.checked && !checkbox.indeterminate) {
      checkbox.indeterminate = true;
    } else if (checkbox.checked && !checkbox.indeterminate) {
      checkbox.checked = false;
    } else {
      checkbox.checked = true;
      checkbox.indeterminate = false;
    }
  });
};

// Clicking the checkbox needs to switch the checkbox back because the above functions handle that
const handleCheckboxClick = (checkbox) => {
  setTimeout(() => {
    checkbox.checked = !checkbox.checked;
  });
};

const defaultIndeterminate = document.querySelectorAll(
  ".default-indeterminate"
);

defaultIndeterminate.forEach((checkbox) => (checkbox.indeterminate = true));

// HANDLE SEARCH
const searchBox = document.getElementById("search-top-left");
const searchInput = document.getElementById("search-input");
const searchOptionsContainer = document.getElementById("search-options");
const searchOptionElements = Array.from(
  searchOptionsContainer.querySelectorAll(".search-option")
);

const hideOptions = () => {
  searchOptionsContainer.classList.add("hide");
  searchInput.blur();
};

// Hide options on escape
searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    hideOptions();
    return;
  }
});

// Hide options if you click somewhere else
document.addEventListener("click", (e) => {
  if (!searchBox.contains(e.target)) {
    hideOptions();
  }
});

const onInputChange = (e) => {
  const value = e.target.value;
  searchOptionElements.forEach((option) => {
    const well = wellMap[option.dataset.id];
    const isMatch = option.dataset.keyword
      .toLowerCase()
      .includes(value.toLowerCase());
    const isShown = wellIsShown(well);

    option.classList[isShown && (!value || isMatch) ? "remove" : "add"]("hide");
  });
};

// Show options on input focus
searchInput.addEventListener("focus", (e) => {
  searchInput.select();
  searchOptionsContainer.classList.remove("hide");
  onInputChange(e);
});

// Filter options on input value change
searchInput.addEventListener("input", onInputChange);

// Handle if search value being clicked
const handleSearchValue = (option) => {
  const well = wellMap[option.dataset.id];
  showWellPopupAndMove(well);
  hideOptions();
  searchInput.value = well.label;
};
