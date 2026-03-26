GW DataLens is a dashboard for viewing and quality-controlling groundwater head time series.

---

## Workflow

1. **Select** a time series. → [Overview](#overview-tab)
2. **Run error detection** to flag suspect measurements. → [Error Detection](#error-detection-tab)
3. **Correct** measurement values where needed. → [Corrections](#corrections-tab)
4. **Review** flagged measurements: accept, reject, or assign labels manually. → [Review](#review-tab)

Optionally, create or inspect time series models used in error detection. → [Models](#time-series-models-tab)

Use the **time range** dropdown (top right) to set the period used for loading and displaying data.

---

### Overview tab

- **Map** (top left): select locations with the mouse or rectangle tool (up to 50).
- **Table** (top right): (Shift+)click rows to plot time series.
- **Chart** (bottom): shows the selected time series.

### Models tab

Create or inspect Pastas time series models (stored in a PastaStore). Models use precipitation and evaporation from the nearest KNMI station and can be used as a reference signal in error detection.

### Error Detection tab

Runs automatic error detection using [`traval`](https://traval.readthedocs.io).

1. Select a time series from the dropdown.
2. Optionally adjust rules and parameters under **Show Parameters**.
3. Click **Run TRAVAL**.

The chart shows suspect measurements and, if available, a Pastas model simulation with prediction interval.

### Corrections tab

Shows all tubes at a location with well configuration and screen depths. Select up to two time series for side-by-side comparison and edit values manually. Optionally use the calculator tool to compute levels relative to NAP. Changes can be committed to the database.

### Review tab

Accept or reject flagged measurements and commit the review to the database, or download results as a CSV file.

---

### References

- [`traval`](https://traval.readthedocs.io/en/latest/) — error detection package
- [`pastas`](https://pastas.dev/) — time series modelling
- [`pastastore`](https://pastastore.readthedocs.io/en/latest/) — model storage
- [`hydropandas`](https://hydropandas.readthedocs.io/en/latest/) — download meteorological data
