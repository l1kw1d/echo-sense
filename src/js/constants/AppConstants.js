var AppConstants = {
  YEAR: "2015",
  SITENAME: "Echo Sense",
  DOWNSAMPLES: [
  	{ value: 0, label: "None" },
  	{ value: 1, label: "Minute" },
    { value: 2, label: "5 Minutes" },
    { value: 3, label: "10 Minutes" },
    { value: 4, label: "Hour" }
  ],
  DOWNSAMPLE_MIN: 1,
  DOWNSAMPLE_TEN_MIN: 2,
  DOWNSAMPLE_HOUR: 3,
  REPORT_DONE: 3,
  REPORT_STATUSES: [
    { value: 1, label: "Created" },
    { value: 2, label: "Generating" },
    { value: 3, label: "Done" },
    { value: 4, label: "Cancelled" },
    { value: 5, label: "Error" }
  ],
  RULE_TRIGGERS: [
    { value: 1, label: "No Data" },
    { value: 2, label: "Floor" },
    { value: 3, label: "Ceiling" },
    { value: 4, label: "In Window" },
    { value: 5, label: "Out of Window" },
    { value: 6, label: "Delta Floor" },
    { value: 7, label: "Delta Ceiling" },
    { value: 8, label: "Any Data" },
    { value: 9, label: "Outside Geofence" },
    { value: 10, label: "Inside Geofence" },
    { value: 11, label: "Outside Radius" },
    { value: 12, label: "Inside Radius" }
  ],
  RULE_PLIMIT_TYPES: [
    { value: -2, label: "Disabled" },
    { value: 1, label: "Second", disabled: true },
    { value: 2, label: "Minute", disabled: true },
    { value: 3, label: "Hour" },
    { value: 4, label: "Day" },
    { value: 5, label: "Week" },
    { value: 6, label: "Month" }
  ],
  WEEKDAYS: [
    { value: 1, label: "Mon" },
    { value: 2, label: "Tue" },
    { value: 3, label: "Wed" },
    { value: 4, label: "Thu" },
    { value: 5, label: "Fri" },
    { value: 6, label: "Sat" },
    { value: 7, label: "Sun" }
  ],
  PAYMENT_STATUSES: [
    { value: 1, label: "Requested" },
    { value: 2, label: "Sent" },
    { value: 3, label: "Confirmed" },
    { value: 4, label: "Failed" }
  ],
  GAP_MINIMUM_SECS: 60,
  DATA_WINDOW_BUFFER_MS: 1000*30,  // 30 secs
  USER_READ: 1,
  USER_RW: 2,
  USER_ACCOUNT_ADMIN: 3,
  USER_ADMIN: 4,
  USER_LABELS: [ "Read", "Read-Write", "Account Admin", "Admin" ],
  USER_STORAGE_KEY: 'echosenseUser'
};

module.exports = AppConstants;