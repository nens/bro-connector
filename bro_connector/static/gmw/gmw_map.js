// Get information
const wells = JSON.parse(document.getElementById("wells_json").textContent);
const organisations = JSON.parse(
  document.getElementById("organisations_json").textContent
);
const glds = JSON.parse(
  document.getElementById("groundwater_level_dossiers_json").textContent
);

// Color map
const colorMapping = {};
const hexToRgb = (hex) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b];
};

// Add color map for each organisation
Object.keys(organisations).forEach((orgKey) => {
  const { organisation_color, organisation_id } = organisations[orgKey];

  // Apply color to html checkbox
  const organisationCheckbox = document.getElementById(
    `checkbox-${organisation_id}`
  );
  organisationCheckbox.style.accentColor = organisation_color;
  organisationCheckbox.style.background = organisation_color;

  // Add color to color map
  const rgbColor = hexToRgb(organisation_color);
  colorMapping[organisation_id] = { color: rgbColor, visible: true };
});

// Create a popup with well information and a link to the object page
const createPopup = (well) => {
  const popup = document.createElement("div");
  const objectPageUrl = `/admin/gmw/groundwatermonitoringwellstatic/${well.object_id}`;
  const popupContent = `
              <div style="background-color: white; padding: 1em; border-radius: 10px">
                <a href="${objectPageUrl}" target="_blank"><strong>${well.bro_id}</strong></a><br>
                Latitude: ${well.latitude}<br>
                Longitude: ${well.longitude}<br>
                Quality regime: ${well.quality_regime}<br>
                Accountable party: ${well.accountable_party}<br>
              </div>
              <div style="display: flex; width: 100%; justify-content: center; padding-bottom: 0.5em;">
                <div style="clip-path: polygon(100% 0, 0 0, 50% 100%); width: 10px; height: 10px; background-color: white;"></div>
              </div>
                  `;
  popup.innerHTML = popupContent;
  return popup;
};

const white = [255, 255, 255];
let marker = null;

// For each well, add a circle
const myScatterplotLayer = new deck.MapboxLayer({
  id: "scatterplot-layer",
  data: wells,
  type: deck.ScatterplotLayer,
  getPosition: (well) => [well.longitude, well.latitude],
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
  getFillColor: (well) => colorMapping[well.organisation_id].color,
  lineWidthMinPixels: 2,
  getLineColor: white,

  //   Hide circle when organisation is set to invicible
  getRadius: (well) => (colorMapping[well.organisation_id].visible ? 10 : 0),

  //   On click add a popup as an Mapbox marker at the circle's location
  onClick: (event) => {
    const well = event.object;
    const popup = createPopup(well);
    const newMarker = new mapboxgl.Marker(popup, { anchor: "bottom" })
      .setLngLat([well.longitude, well.latitude])
      .addTo(map);
    setTimeout(() => (marker = newMarker));
  },
});

// Create the map
const map = new mapboxgl.Map({
  container: "deck-gl-canvas",
  style:
    "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
  antialias: true,
  center: [3.945697, 51.522601],
  zoom: 9,
  bearing: 0,
  pitch: 0,
});

// Add map control and circle layer
map.addControl(new mapboxgl.NavigationControl(), "bottom-left");
map.on("load", () => map.addLayer(myScatterplotLayer));

// Remove popup on map click
map.on("click", () => marker && marker.remove());

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

// Handle if someone toggles and organisation
const handleOrganisationClick = (id, element) => {
  const checkbox = element.querySelector('input[type="checkbox"]');
  const colorMap = colorMapping[id];
  colorMap.visible = !colorMap.visible;
  checkbox.checked = colorMap.visible;
  //   Updating the update triggers to Date.now() makes sure the getRadius gets recaluclated
  myScatterplotLayer.setProps({
    updateTriggers: {
      getRadius: Date.now(),
    },
  });
};

// Clicking the checkbox needs to switch the checkbox back because the above function handles that
const handleCheckboxClick = (checkbox) =>
  setTimeout(() => (checkbox.checked = !checkbox.checked));
