// Get information
const wells = JSON.parse(document.getElementById("wells_json").textContent);
const glds = JSON.parse(
  document.getElementById("glds_json").textContent
);
const wellMap = Object.fromEntries(
  wells.map((well) => [well.groundwater_monitoring_well_static_id + "", well])
);

const colorMap = {};

const hexToRgb = (hex) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b, 200];
};

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

// Create popup with well info + GLD entries
const createPopup = (well) => {  
  const glds_well = findObjectsByIds(well.glds, glds);
  const popup = document.createElement("div");
  const objectPageUrl = `/admin/gmw/groundwatermonitoringwellstatic/${well.groundwater_monitoring_well_static_id}`;  
  const BROloketUrl = `https://www.broloket.nl/ondergrondgegevens?bro-id=${well.bro_id}`;

  let gldsContent = "";
  if (glds_well.length > 0) {
    glds_well.forEach((gld, i) => {
      const GLDPageUrl = `/admin/gld/groundwaterleveldossier/${gld.groundwater_level_dossier_id}`;
      const GLDBROID = gld.gld_bro_id;
      const tube_number = gld.tube_number;
      const measurementType = gld.latest_measurement_date ? "regulier" : "controle";
      const status = gld.status;
      const latestDate = formatDate(gld.latest_measurement_date);
      const color = getDateColor(gld.latest_measurement_date);

      gldsContent += `
        <details style="margin-bottom:6px;">
          <summary style="cursor:pointer;font-weight:bold;">
            Filter ${tube_number}
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
            <span class="label">Type:</span>
            <span class="value">${measurementType}</span>
          </div>
          <div class="well-item">
            <span class="label">Status:</span>
            <span class="value">${status}</span>
          </div>
          <div class="well-item">
            <span class="label">Latest measurement:</span>
            <span class="value">${latestDate}</span>
          </div>
        </details>
      `;
    });
  } else {
    gldsContent = `<div class="well-item"><em>No GLD entries found</em></div>`;
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
  // Hide if doenst have linked_gmns and notLinked is false or if visibileMap doesnt have any of the linked gmns
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

function getColorFromGLD(gld) {
  return getDateColor(gld.latest_measurement_date)
}

function renderPieToCanvas(data, size = 64) {
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


// 2. Function to build pie icon data for all wells
const pieData = wells.map((well) => { 
  const gldsData = getGLDs(well.glds); 
  const pieChart = gldsData.map(gld => ({ 
    color: getColorFromGLD(gld) 
  })); 
  const iconUrl = renderPieToCanvas(pieChart); 
  return { 
    position: [well.y, well.x], 
    well,   // <-- store this for dynamic resizing
    iconUrl, 
  }; 
});

// 3. Function to generate IconLayer with dynamic size
const pieIconLayer = new deck.MapboxLayer({
  id: "pie-layer",
  type: deck.IconLayer,
  data: pieData,
  pickable: true,
  getPosition: d => d.position,
  getIcon: d => ({
    url: d.iconUrl,
    width: 64,
    height: 64,
    anchorY: 32,
  }),
  sizeUnits: "pixels",
  getSize: d => wellIsShown() ? 25 : 0, // diameter
    //   On click add a popup as an Mapbox marker at the circle's location
  onClick: (event) => {
    const well = event.object.well;
    showWellPopupAndMove(well);
  },
});

function createTextLayer(visible) {
  const visibleWells = wells;

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

// Function to open validation map with current view
function switchToBaseMap() {
  // Get current map center and zoom
  const center = map.getCenter();
  const zoom = map.getZoom();
  
  // Create URL with current view parameters
  const url = `../?lng=${center.lng}&lat=${center.lat}&zoom=${zoom}`;
  
  // Open in new tab
  window.location.href = url;
}

// Function to get URL parameters and set initial view
function setInitialViewFromURL() {
  const params = new URLSearchParams(window.location.search);
  const lng = params.get('lng');
  const lat = params.get('lat');
  const zoom = params.get('zoom');
  
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
  
  updateGetRadius();
  updateTextLayer();
};

const deselectAllCheckboxes = () => {
  updateGetRadius();
  updateTextLayer();
};

// Handle if someone toggles an gmn
const handleTypeClick = (id, element) => {
  updateGetRadius();
  updateTextLayer();
};

const updateGetRadius = () => {
  //   Updating the update triggers to Date.now() makes sure the getRadius gets recaluclated
  pieIconLayer.setProps({
    updateTriggers: {
      getRadius: Date.now(),
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
