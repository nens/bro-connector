The QC Dashboard contains 2 tabs to interact with groundwater head time series.

---

### Overview tab

The overview tab consists of three elements: 
   * Map view showing measurement locations
   * Table showing measurement location metadata
   * Chart for plotting time series

There are two ways of plotting head time series:
   * Select one or multiple measurement locations on the map using your mouse or the rectangle selection tool 
   * Click on any row in the table

### QC tab

The QC tab lets you run automatic error detection schemes on head time series (see the [`traval`](https://traval.readthedocs.io) package). The rules that comprise the error detection algorithm are shown in the bottom-left table.

Steps:
   1. Use the first dropdown to select or search for any time series in the database.
   2. Optionally use the second dropdown to plot additional time series for comparison purposes.
   3. Press the "Run TRAVAL" button.
   4. The chart will update showing the original time series and the measurements that were deemed suspect by the error detection algorithm. If available a pastas model simulation and prediction interval are also shown in the chart. The observations that are marked as suspect by the algorithm are listed in the bottom-right table.
