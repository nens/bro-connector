The GW DataLens dashboard can be used to validate groundwater measurements.

---

The validation process consists of the following steps:

   1. Select a head time series from a database. ([Overview](#overview-tab))
   2. Run a set of error-detection rules to identify potentially suspect measurements. ([Error Detection](#error-detection-tab))
   3. The time series is manually reviewed (accepting or rejecting) suggestions made by the  error detection algorithm. ([Manual Review](#error-detection-tab))

Optionally, time series models can be inspected or created using the [Time Series Models](#time-series-models-tab) tab. These models can be used in the error detection step.

### Overview tab

The overview tab consists of three elements:

* Interactive map view showing measurement locations (top left)
* Interactive table showing measurement location metadata (top right)
* Interactive chart showing time series (bottom)

There are two ways of plotting head time series:

* Select one or multiple (up to 10) measurement locations on the map using your
     mouse or the rectangle selection tool.
* (Shift+)Click on row(s) in the table.

### Time Series Models tab

The time series models tab allows users to create or inspect time series models using
Pastas and Pastastore. Models are created using precipitation and evaporation from the
nnearest KNMI station.

### Error Detection tab

The Error Detection tab lets you run automatic error detection schemes on head time
series (see the [`traval`](https://traval.readthedocs.io) package). The rules that
comprise the error detection algorithm are shown in the expandable section at the
bottom. The error detection rules that are applied can be modified or adjusted in the
dashboard.

Steps:

   1. Use the first dropdown to select or search for any time series in the database.
   2. Optionally modify the rules or parameters used for error detection under the `Show Parameters` button.
   3. Press the "Run TRAVAL" button.
   4. The chart will update showing the original time series and the measurements that were deemed suspect by the error detection algorithm. If available a pastas model simulation and prediction interval are also shown in the chart.

### Manual Review tab

The Manual Review tab lets you review the results of the error detection scheme and
commit your manual review to the database, or download the results as a CSV file.

### References

* Documentation for [traval](https://traval.readthedocs.io/en/latest/).
* Documentation for [pastas](https://pastas.dev/).
* Documentation for [pastastore](https://pastastore.readthedocs.io/en/latest/).
