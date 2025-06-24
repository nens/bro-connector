// Get information
const wells = JSON.parse(document.getElementById("wells_json").textContent);
const wellMap = Object.fromEntries(
  wells.map((well) => [well.groundwater_monitoring_well_static_id + "", well])
);

const colorMap = {};
const hexToRgb = (hex) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b];
};

const wellIsShown = (well) => {
  return true;
};

const WHITE = [255, 255, 255];
const BLUE = [0, 0, 255, 150];
const BLACK = [0, 0, 0];
let marker = null;

// For example, if you want all parties to be blue:
wells.forEach(well => {
  colorMap[well.delivery_accountable_party] = BLUE;
});
// Get URL parameters
const urlParams = new URLSearchParams(window.location.search);
const lat = parseFloat(urlParams.get("lat"));
const lon = parseFloat(urlParams.get("lon"));

// Use URL params or fallback to default center
const initialCenter = (lat && lon) ? [lon, lat] : [3.945697, 51.522601];

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

function createTextLayer(visible) {
  return new deck.MapboxLayer({
    id: "text-layer",
    data: wells,
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
  center: initialCenter,
  zoom: 14,
  bearing: 0,
  pitch: 0,
});

// Add map control and circle layer
map.addControl(new mapboxgl.NavigationControl(), "bottom-left");
map.on("load", () => {
  map.addLayer(myScatterplotLayer);
  const zoom = map.getZoom();
  const shouldShowText = zoom >= 12;
  const newTextLayer = createTextLayer(shouldShowText);
  map.addLayer(newTextLayer);
});


map.on("zoom", () => {
  const zoom = map.getZoom();
  const shouldShowText = zoom >= 12;
  isTextLayerVisible = shouldShowText;
  // Remove the old layer if it exists
  if (map.getLayer("text-layer")) {
    map.removeLayer("text-layer");
  }
  // Add it back with correct visibility
  const newTextLayer = createTextLayer(shouldShowText);
  map.addLayer(newTextLayer);
});

// Remove popup on map click
map.on("click", () => marker && marker.remove());

// Get the toggle button element
const toggleTextLayerButton = document.getElementById("toggle-text-layer-btn");

// Variable to keep track of the layer's visibility state
let isTextLayerVisible = true;

// Function to toggle the visibility of the text layer
const toggleTextLayerVisibility = () => {
  const zoom = map.getZoom();
  const shouldShowText = zoom >= 12;
  const newTextLayer = createTextLayer(shouldShowText);
  try {
    if (isTextLayerVisible) {
      // If the text layer is visible, remove it from the map
      if (map.getLayer("text-layer")) {  // Check if the layer exists before removing it
        map.removeLayer("text-layer");
      } else {
        console.warn("Text layer not found, nothing to remove.");
      }
    } else {
      // If the text layer is not visible, add it back to the map
      if (!map.getLayer("text-layer")) {  // Check if the layer doesn't already exist
        map.addLayer(newTextLayer);
      } else {
        console.warn("Text layer already exists on the map.");
      }
    }
    // Toggle the visibility state
    isTextLayerVisible = !isTextLayerVisible;
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
