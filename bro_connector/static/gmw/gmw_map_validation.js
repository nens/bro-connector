// Get information
const allWells = JSON.parse(document.getElementById("wells_json").textContent);
const glds = JSON.parse(document.getElementById("glds_json").textContent);
const state = JSON.parse(document.getElementById("state_json").textContent);
console.log(state.checkboxes)
const idSet = new Set(state.ids);
const wells = allWells.filter(well => idSet.has(well.groundwater_monitoring_well_static_id));
const wellMap = Object.fromEntries(
  wells.map((well) => [well.groundwater_monitoring_well_static_id + "", well])
);

const visibleMap = {
  no_glds: true,
  type: {
    no_obs: true,
    controle: true,
    regular: true,
  },
  status: {
    no_status: true,
    validated: true,
    tentative: true,
    unknown: true,
  }
}; // update visible map wells / glds depending on selected toggles

const colorMap = {};

const hexToRgb = (hex) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b, 200];
};

const valueMap = {
  type: {
    controle: "controlemeting",
    regular: "reguliereMeting",
    none: null
  },
  status: {
    validated: "volledigBeoordeeld",
    tentative: "voorlopig",
    unknown: "onbekend",
    none: null,
  }  
}

// Show check or cross
const checkOrCross = (boolean) => (boolean ? "&check;" : "&cross;");

function findObjectsByIds(ids, glds) {
  gld_unsorted = ids.map(id => 
    glds.find(gld => gld.groundwater_level_dossier_id === id)
  );
  
  return gld_unsorted.slice().sort((a, b) => a.tube_number - b.tube_number);
  // ).filter(Boolean); // filter(Boolean) removes null/undefined if no match found
}
// function findObjectsByIds(ids, glds) {
//   return ids.map(id => {
//     const matched = glds.filter(gld => gld.groundwater_level_dossier_id === id)
//                         .sort((a, b) => a.tube_number - b.tube_number); // lowest tube_number first
//     return matched.length > 0 ? matched[0] : { groundwater_level_dossier_id: id }; // keep id if no match
//   });
// }

// Helper: format date nicely
function formatString(string) {
  if (!string) return "—";
  return string
}
// Helper: format date nicely
function formatDate(dateString) {
  if (!dateString) return "—";
  const d = new Date(dateString);
  return d.toLocaleDateString();
}

// Helper: determine color based on recency of date
function getDateColor(dateString) {
  if (!dateString) return '#9E9E9E'; // no measurement
  const now = new Date();
  const d = new Date(dateString);
  const diffYears = (now - d) / (1000 * 60 * 60 * 24 * 365);

  if (diffYears < 1) return '#4CAF50';      // measured within a year
  if (diffYears < 2) return '#FFC107';     // measured within 5 years
  return '#F44336';                           // older
}

function getFilterStatus(well) {
  let filterStatus = "Geen GLDs voor deze put"
  if (well.glds.length === 0) {
    return filterStatus;
  }
  const { type } = visibleMap;
  filterStatus += " na filteren op:"
  if (!type.no_obs) {
    filterStatus += "<br>• Geen meting"
  }
  if (!type.controle) {
    filterStatus += "<br>• Controle meting"
  }
  if (!type.regular) {
    filterStatus += "<br>• Reguliere meting"
  }

  return filterStatus
}

// Create popup with well info + GLD entries
const createPopup = (well) => { 
  const glds_well = filterGLDs(findObjectsByIds(well.glds, glds), well); // should be visibleMap something
  const popup = document.createElement("div");
  const objectPageUrl = `/admin/gmw/groundwatermonitoringwellstatic/${well.groundwater_monitoring_well_static_id}`;  
  const BROloketUrl = `https://www.broloket.nl/ondergrondgegevens?bro-id=${well.bro_id}`;

  let gldsContent = "";
  if (glds_well.length > 0) {
    glds_well.forEach((gld, i) => {
      const GLDPageUrl = `/admin/gld/groundwaterleveldossier/${gld.groundwater_level_dossier_id}`;
      const GLDBROID = formatString(gld.gld_bro_id);
      const tube_number = gld.tube_number;
      const measurementType = formatString(gld.observation_type);
      const status = formatString(gld.status);
      const latestDate = formatDate(gld.latest_measurement_date);
      const color = getDateColor(gld.latest_measurement_date);

      gldsContent += `
        <details style="margin-bottom:6px;">
          <summary style="cursor:pointer;font-weight:bold;">
            Filterbuis ${tube_number}
          </summary>
          <div style="width: 100%; height: 6px; margin: 4px 0; border-radius: 3px; background-color: ${color};"></div>
          <div class="well-item">
            <span class="label">GLD:</span>
            <span class="value"><a href="${GLDPageUrl}" target="_blank">GLD Link</a></span>
          </div>
          <div class="well-item">
            <span class="label">BRO ID:</span>
            <span class="value">${GLDBROID}</span>
          </div>
          <div class="well-item">
            <span class="label">Observatie type:</span>
            <span class="value">${measurementType}</span>
          </div>
          <div class="well-item">
            <span class="label">Validatiestatus:</span>
            <span class="value">${status}</span>
          </div>
          <div class="well-item">
            <span class="label">Meest recente meting:</span>
            <span class="value">${latestDate}</span>
          </div>
        </details>
      `;
    });
  } else {
    gldsContent = `<div class="well-item"><em>${getFilterStatus(well)}</em></div>`;
  }

  const popupContent = `
    <div id="popup-content">
      <a href="${objectPageUrl}" target="_blank">
        <strong style="font-size: 18px;">${well.well_code}</strong>
      </a>
      <hr width="100%" size="2">
      <div class="well-item">
        <span class="label">BRO-ID:</span>
        <span class="value">${well.bro_id}</span>
      </div>
      <div class="well-item">
        <span class="label">BRO-loket:</span>
        <span class="value"><a href="${BROloketUrl}" target="_blank">broloket link</a></span>
      </div>
      ${gldsContent}
    </div>
    <div style="display: flex; width: 100%; justify-content: center; padding-bottom: 0.5em;">
      <div style="clip-path: polygon(100% 0, 0 0, 50% 100%); width: 10px; height: 10px; background-color: white;"></div>
    </div>
  `;

  popup.innerHTML = popupContent;
  popup.addEventListener("click", (e) => {
    e.stopPropagation();
  });
  popup.addEventListener("mouseenter", () => {
    map.scrollZoom.disable();
  });
  popup.addEventListener("mouseleave", () => {
    map.scrollZoom.enable();
  });

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
  if (well.glds.length === 0 && !visibleMap.no_glds)
    return;

  if (well.glds.length > 0 && !filterGLDs(getGLDs(well.glds), well).length)
    return;

return true;
};    

const WHITE = [255, 255, 255];
const BLACK = [0, 0, 0];
let marker = null;

// For each well, add a circle
// const myScatterplotLayer = new deck.MapboxLayer({
//   id: "scatterplot-layer",
//   data: wells,
//   type: deck.ScatterplotLayer,
//   getPosition: (well) => [well.y, well.x],
//   pickable: true,
//   radiusMaxPixels: 6.5,
//   radiusUnits: "meters",
//   lineWidthMaxPixels: 1,
//   lineWidthUnits: "meters",
//   getLineWidth: 0.005,
//   stroked: true,
//   filled: true,
//   antialiasing: true,
//   radiusUnits: "pixels",
//   getFillColor: (well) => colorMap[well.delivery_accountable_party],
//   lineWidthMinPixels: 2,
//   getLineColor: WHITE,

//   // Hide circle when gmn or organisation is set to invisible
//   getRadius: (well) => (wellIsShown(well) ? 10 : 0),

//   //   On click add a popup as an Mapbox marker at the circle's location
//   onClick: (event) => {
//     const well = event.object;
//     showWellPopupAndMove(well);
//   },
// });

const getGLDs = (ids) => {
  return glds
    .filter(gld => ids.includes(gld.groundwater_level_dossier_id))
    .sort((a, b) => a.tube_number - b.tube_number); // lowest first
};

const filterGLDsByStatus = (glds) => {
  if (!visibleMap.status.no_status) {
    glds = glds.filter(gld => gld.status != valueMap.status.none);
  }

  if (!visibleMap.status.validated) {
    glds = glds.filter(gld => gld.status !== valueMap.status.validated);
  }

  if (!visibleMap.status.tentative) {
    glds = glds.filter(gld => gld.status !== valueMap.status.tentative);
  }

  if (!visibleMap.status.unknown) {
    glds = glds.filter(gld => gld.status !== valueMap.status.unknown);
  }

  return glds
}

const filterGLDs = (glds, well) => {

  if (well.bro_id === "GMW000000051044") {
      console.log("visibleMap: ", visibleMap);
      console.log(well.status);
    }

  if (!visibleMap.type.no_obs) {
    glds = glds.filter(gld => gld.observation_type != valueMap.type.none);
  }

  if (!visibleMap.type.controle) {
    glds = glds.filter(gld => gld.observation_type !== valueMap.type.controle);
  }  
  
  if (!visibleMap.type.regular) {
    glds = glds.filter(gld => gld.observation_type !== valueMap.type.regular);
  }  

  if (glds.length > 0) {
    return filterGLDsByStatus(glds)
  }
  // make sure that is it hierarchical

  return glds
};

function getColorFromGLD(gld) {
  return getDateColor(gld.latest_measurement_date)
}

function renderPieToCanvas(data, empty = false, size = 64) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2;

  let total = data.length;
  let startAngle = -0.5 * Math.PI;
  // console.log(data)
  // console.log(startAngle)

  if (empty) {
    // Fill with transparent grey
    ctx.beginPath();
    ctx.arc(cx, cy, radius - 1, 0, 2 * Math.PI);
    ctx.fillStyle = "rgba(158, 158, 158, 0.05)"; // grey with ~20% opacity
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx, cy, radius - 1, 0, 2 * Math.PI); // subtract 1 so stroke fits inside
    ctx.strokeStyle = '#9E9E9E';
    ctx.lineWidth = 5;  
    ctx.stroke();

    // Small dot in the center
    ctx.beginPath();
    ctx.arc(cx, cy, size * 0.05, 0, 2 * Math.PI); // dot radius = 5% of size
    ctx.fillStyle = '#9E9E9E';
    ctx.fill();

    return canvas.toDataURL();
  }

  for (const slice of data) {
    const angle = (1 / total) * 2 * Math.PI;
    // console.log(startAngle, startAngle + angle)
    // console.log(slice.color)
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, startAngle, startAngle + angle);
    ctx.closePath();
    ctx.fillStyle = slice.color;
    ctx.fill();
    if (total > 1) {
      ctx.strokeStyle = "white";
      ctx.lineWidth = 2;  // adjust thickness
      ctx.stroke();
    }
    startAngle += angle;
  }

  // Append a timestamp to force Deck.gl to treat it as a new image
  return canvas.toDataURL();
}

function buildPieData() {
  return wells.map((well) => { 
    const gldsData = getGLDs(well.glds); 
    const gldsDataFiltered = filterGLDs(gldsData, well);

    if (well.bro_id === "GMW000000051044") {
      console.log("GLDs before filter:", gldsData.length);
      console.log("GLDs after filter:", gldsDataFiltered.length);
    }

    const pieChart = gldsDataFiltered.map(gld => ({
      color: getColorFromGLD(gld) 
    })); 

    const iconUrl = renderPieToCanvas(pieChart, well.glds.length < 1); 

    return {  
      well,
      iconUrl, 
    }; 
  });
}

// 3. Function to generate IconLayer with dynamic size
const pieIconLayer = new deck.MapboxLayer({
  id: "pie-layer",
  type: deck.IconLayer,
  data: buildPieData(),
  pickable: true,
  getPosition: d => [d.well.y, d.well.x],
  getIcon: d => ({
    url: d.iconUrl,
    width: 64,
    height: 64,
    anchorY: 32,
  }),
  sizeUnits: "pixels",
  getSize: d => wellIsShown(d.well) ? 25 : 0, // diameter
  onClick: (event) => {
    const well = event.object.well;
    showWellPopupAndMove(well);
  },
});

function createTextLayer(visible) {
  return new deck.MapboxLayer({
    id: "text-layer",
    data: wells,
    type: deck.TextLayer,
    getPosition: (well) => [well.y, well.x],
    getText: (well) => well.label + "",
    getAlignmentBaseline: "bottom",
    getColor: BLACK,
    getSize: (well) => (wellIsShown(well) ? 100 : 0),
    sizeUnits: "meters",
    sizeMaxPixels: 15,
    getPixelOffset: [50, -30],
    getTextAnchor: "middle",
    getAngle: 30,
    visible: visible,
    updateTriggers: {
      getSize: Date.now(), // forces Deck.gl to reevaluate sizes
    },
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

// Function to open validation map with current view
async function switchToBaseMap() {
  // Get current map center and zoom
  const center = map.getCenter();
  const zoom = map.getZoom();
  const visibleWells = wells
  const visibleIds = visibleWells.map(w => w.groundwater_monitoring_well_static_id);
  console.log("IDs length: ",visibleIds.length)

  const payload = {
    ids: visibleIds,
    lon: center.lng,
    lat: center.lat,
    zoom: zoom,
    checkboxes: state.checkboxes,
  };

  try {
    // 1. Post visible IDs to Django and wait until it's done
    const resp = await fetch("/map/state/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // "X-CSRFToken": getCookie("csrftoken")  // if CSRF is active
      },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      console.error("Failed to store visible wells:", resp.status);
      return;
    }

    // 2. Only redirect after success
    const url = `../`;
    window.location.href = url;

  } catch (err) {
    console.error("Error storing visible wells:", err);
  }
}

// Function to get URL parameters and set initial view
function setInitialViewFromURL() {
  const lng = state.lon;
  const lat = state.lat;
  const zoom = state.zoom;
  
  if (lng && lat && zoom) {
    return {
      center: [parseFloat(lng), parseFloat(lat)],
      zoom: parseFloat(zoom)
    };
  }
  
  // Return default view if no parameters
  return {
    center: [3.945697, 51.522601], // Default Netherlands center
    zoom: 9
  };
}

// Create the map
const initialView = setInitialViewFromURL();
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
  center: initialView.center,
  zoom: initialView.zoom,
  bearing: 0,
  pitch: 0,
});

// Add map control and circle layer
map.addControl(new mapboxgl.NavigationControl(), "bottom-left");
map.on("load", () => {
  // map.addLayer(myScatterplotLayer);
  map.addLayer(pieIconLayer);
});

// regenerate all icons on zoom:

map.on("zoom", () => {
  // console.log(map.getZoom())
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
  
  updateGetSize();
  updateTextLayer();
};

const deselectAllCheckboxes = () => {
  if (!visibleMap || !visibleMap.type) {
    console.warn("❌ visibleMap.type not defined");
    return;
  }

  const type = visibleMap.type;
  console.log("🔍 Current visibleMap.type state:", type);

  // Check if any GMN is false
  const anyFalse = Object.values(type).some(value => value === false);
  console.log(`❓ Any type false? ${anyFalse}`);

  // Decide the new state: if any false => set all true; else set all false
  const newState = anyFalse ? true : false;
  console.log(`➡️ Setting all types to: ${newState}`);

  // Update visibleMap.gmns
  Object.keys(type).forEach(key => {
    type[key] = newState;
  });
  console.log(visibleMap)

  // Sync checkboxes with visibleMap.gmns state
  Object.keys(type).forEach(key => {
    let searchKey = key;
    const escapedKey = CSS.escape(searchKey);
    const checkbox = document.querySelector(`#checkbox-${escapedKey}`);
    if (checkbox) {
      checkbox.checked = newState;
      console.log(`✔️ Checkbox for '${searchKey}' set to ${newState}`);
    } else {
      console.warn(`⚠️ Checkbox #checkbox-${searchKey} not found in DOM`);
    }
  });

  updateGetData();
  updateGetSize();
  updateTextLayer();
};

const deselectAllStatusCheckboxes = () => {
  if (!visibleMap || !visibleMap.status) {
    console.warn("❌ visibleMap.status not defined");
    return;
  }

  const status = visibleMap.status;
  // console.log("🔍 Current visibleMap.type state:", status);

  // Check if any status is false
  const anyFalse = Object.values(status).some(value => value === false);
  // console.log(`❓ Any type false? ${anyFalse}`);

  // Decide the new state: if any false => set all true; else set all false
  const newState = anyFalse ? true : false;
  // console.log(`➡️ Setting all status to: ${newState}`);

  // Update visibleMap.status
  Object.keys(status).forEach(key => {
    status[key] = newState;
  });

  // Sync checkboxes with visibleMap.status state
  Object.keys(status).forEach(key => {
    let searchKey = key;
    const escapedKey = CSS.escape(searchKey);
    const checkbox = document.querySelector(`#checkbox-${escapedKey}`);
    if (checkbox) {
      checkbox.checked = newState;
      console.log(`✔️ Checkbox for '${searchKey}' set to ${newState}`);
    } else {
      console.warn(`⚠️ Checkbox #checkbox-${searchKey} not found in DOM`);
    }
  });

  updateGetData();
  updateGetSize();
  updateTextLayer();
};



// Handle if someone toggles an type measurement
const handleTypeClick = (id, element) => {
  // console.log(id)
  const checkbox = element.querySelector('input[type="checkbox"]');
  const { type } = visibleMap;

  if (id === "no_glds") {
    visibleMap[id] = !visibleMap[id]
    checkbox.checked = visibleMap[id];
    updateGetSize();
    updateTextLayer();
    return;
  }

  type[id] = !type[id];
  checkbox.checked = type[id];

  updateGetData();
  updateGetSize();
  updateTextLayer();
};

// Handle if someone toggles an status measurement
const handleStatusClick = (id, element) => {
  // console.log(id)
  const checkbox = element.querySelector('input[type="checkbox"]');
  const { status } = visibleMap;
  
  status[id] = !status[id];
  checkbox.checked = status[id];

  updateGetData();
  updateGetSize();
  updateTextLayer();
};

const updateGetData = () => {
  // console.log("updating data")
  pieIconLayer.setProps({
    data: buildPieData(),
    updateTriggers: {
      data: Date.now(),
    },
  });
}


const updateGetSize = () => {
  //   Updating the update triggers to Date.now() makes sure the getRadius gets recaluclated
  pieIconLayer.setProps({
    updateTriggers: {
      getSize: Date.now(),
    },
  });
};

// Clicking the checkbox needs to switch the checkbox back because the above functions handle that
const handleCheckboxClick = (checkbox) => {
  setTimeout(() => {
    checkbox.checked = !checkbox.checked;
  });
};

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
