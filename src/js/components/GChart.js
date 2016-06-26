
var React = require('react');

var GChart = React.createClass({displayName: 'GChart',
  getDefaultProps: function() {
    return {
      id: "_chart",
      visible: true,
      columns: [], // Array of 2-3-item arrays [type, label, id(optional)]
      divClass: "_gchart",
      type: 'LineChart',
      title: 'Chart Title',
      width: null, // Use container's width
      height: null, // Use container's height
      options: null,
      series: {},
      pointSize: 13,
      data: [],
      dataSourceUrl: null,
      toolbar: false,
      allow_download: false
    };
  },
  getInitialState: function() {
    return {
      dataTable: this.props.dataSourceUrl ? null : new google.visualization.DataTable(),
      wrapper: null
    }
  },
  componentDidMount: function() {
    this.fullInitialize();
  },
  getChart: function() {
    var cw = this.state.wrapper;
    if (cw) return cw.getChart();
    return null;
  },
  fullInitialize: function() {
    var that = this;
    this.initializeDataTable(function() {
      that.initializeWrapper(that.draw);
    });
  },
  initializeDataTable: function(callback) {
    var dt = new google.visualization.DataTable();
    if (dt) {
      // Add columns and data from props
      for (var i in this.props.columns) {
        var c = this.props.columns[i];
        if (Array.isArray(c)) dt.addColumn(c[0], c[1]);
        else dt.addColumn(c); // Cols as objects
        console.log(c);
      }
      if (this.props.data.length > 0) {
        console.log("Adding "+this.props.data.length+" row(s)");
        dt.addRows(this.props.data);
      }
      this.setState({dataTable: dt}, function() {
        if (callback) callback();
      });
      console.log("Initialized data table with "+dt.getNumberOfColumns()+" column(s) and "+this.props.data.length+" row(s)");
    } else {
      if (callback) callback();
    }
  },
  setTable: function(dt, opts, chartType) {
    // For passing data from parent
    if (this.state.wrapper) {
      var cw = this.state.wrapper;
      cw.setDataTable(dt);
      if (opts) {
        cw = this.setOptions(cw, opts, false);
      }
      if (chartType) cw.setChartType(chartType);
      this.setState({dataTable: dt, wrapper: cw}, function() {
        this.draw();
      });
    }
  },
  setOptions: function(cw, opts, _do_draw) {
    var do_draw = _do_draw == null ? true : _do_draw;
    if (!cw) cw = this.state.wrapper;
    if (cw) {
      for (var key in opts) {
        if (opts.hasOwnProperty(key)) {
          cw.setOption(key, opts[key]);
        }
      }
      if (do_draw) this.draw();
    }
    return cw;
  },
  getOptions: function() {
    var opts = {
        'title': this.props.title,
        'pointSize': this.props.pointSize,
        'series': this.props.series,
        'animation': {duration: 1000, easing: 'out'}
      };
    if (this.props.width) opts.width = this.props.width;
    if (this.props.height) opts.height = this.props.height;
    if (this.props.options) {
      for (var key in this.props.options) {
        if (this.props.options.hasOwnProperty(key)) {
          opts[key] = this.props.options[key];
        }
      }
    }
    return opts;
  },
  initializeWrapper: function(callback) {
    var opts = this.getOptions();
    var wrapper = this.state.wrapper;
    if (wrapper == null) wrapper = new google.visualization.ChartWrapper({
      chartType: this.props.type,
      options: opts,
      containerId: this.props.id
    });
    if (this.state.dataTable) wrapper.setDataTable(this.state.dataTable);
    if (this.props.dataSourceUrl) wrapper.setDataSourceUrl(this.props.dataSourceUrl);
    if (opts) wrapper.setOptions(opts);
    console.log("Initialized wrapper in container '"+this.props.id+"', type: "+this.props.type);
    this.setState({wrapper: wrapper}, function() {
      if (callback) callback();
    });
  },
  draw: function() {
    console.log("Trying to draw");
    if (this.state.wrapper && ((this.state.dataTable && this.state.dataTable.getNumberOfColumns() > 0) || this.props.dataSourceUrl)) {
      this.state.wrapper.draw();
      if (this.props.allow_download){
        google.visualization.events.addListener(this.state.wrapper, 'ready', this.addDownloadLink);
      }
      if (this.props.afterDraw) this.props.afterDraw();
    } else console.log("No data to draw");
  },

  addDownloadLink: function() {
      var chart = this.state.wrapper.getChart();
      $("#"+this.props.id).append('<a id="chart_download" class="btn btn-info btn-sm" title="Right Click -> Save Link As" download="Echo Mobile Chart" target="_blank" href="'+chart.getImageURI()+'">Download image</a>');
  },

  render: function() {
    return (
      <div id={this.props.id} hidden={!this.props.visible} className={this.props.divClass}>
      </div>
      );
  }
});

module.exports = GChart;