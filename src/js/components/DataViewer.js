var React = require('react');
var Router = require('react-router');

var $ = require('jquery');
var util = require('../utils/util');
var LoadStatus = require('./LoadStatus');
var EntityMap = require('./EntityMap');
var GChart = require('./GChart');
var moment = require('moment');
var Select = require('react-select');
var mui = require('material-ui');
var FlatButton = mui.FlatButton;
var Dialog = mui.Dialog;
var AppConstants = require('../constants/AppConstants');
var IconMenu = mui.IconMenu;
var MenuItem = mui.MenuItem;
var DatePicker = mui.DatePicker;
var TimePicker = mui.TimePicker;
var toastr = require('toastr');

export default class DataViewer extends React.Component {
    static contextTypes = {
        router: React.PropTypes.func
    }
    static defaultProps = { user: null };

    constructor(props) {
        super(props);
        this.state = {
            sensor: null,
            records: [],
            loading: false,
            datapoint_dlg_open: false
        };
    }

    componentDidMount() {
        var that = this;
        this.fetchSensor(); // Calls fetchData
    }
    componentWillReceiveProps(nextProps) {
        var prior_col = this._vis_column();
        var gc_needs_update = prior_col != nextProps.location.query.col && this.refs.chart != null;
        if (gc_needs_update) {
            this.refreshChart();
        }
    }
    componentDidUpdate(prevProps, prevState) {
        // Gchart needs update?
    }
    _vis_column() {
        return this.props.location.query.col;
    }
    _list_columns() {
        var listcols = this.props.location.query.listcols;
        if (listcols) return listcols.split(',');
        else return [];
    }
    _downsample() {
        return parseInt(this.props.location.query.ds);
    }
    _ts_start() {
        var ts_now = util.nowTimestamp();
        var ts_start = parseInt(this.props.location.query.sta) || (ts_now - 1000*60*60*2);
        return ts_start;
    }
    _ts_end() {
        var ts_now = util.nowTimestamp();
        var ts_end = parseInt(this.props.location.query.end) || (ts_now);
        return ts_end;
    }
    _start_date() {
        return new Date(this._ts_start());
    }
    _end_date() {
        return new Date(this._ts_end());
    }
    _date_time_value(start_or_end, date_or_time) {
        var ts;
        if (start_or_end == 'end') ts = this._ts_end();
        else ts = this._ts_start();
        if (date_or_time == 'time') return 0;
        else return 0;
    }
    noData() {
        return this.state.records.length == 0;
    }
    getSchema() {
        var s = this.state.sensor;
        if (s && s.sensortype) return JSON.parse(s.sensortype.schema);
        return null;
    }
    fetchSensor() {
        var that = this;
        var kn = this.props.params.sensorKn;
        if (kn) {
            var data = {
                'with_sensortype': 1
            };
            $.getJSON("/api/sensor/"+kn, data, function(res) {
                if (res.success) {
                    var sensor = res.data.sensor;
                    that.setState({sensor: sensor, loading: false}, function() {
                        if (that.noData()) that.fetchData();
                    });
                } else that.setState({loading: false});
            });
        }
    }

    fetchData() {
        var that = this;
        if (this.state.sensor) {
            var s = this.state.sensor;
            this.setState({loading: true, records: []});
            var data = {
                'sensor_kn': s.kn,
                'ts_start': this._ts_start(),
                'ts_end': this._ts_end(),
                'downsample': this._downsample()
            };
            $.getJSON("/api/data", data, function(res) {
                if (res.success) {
                    var records = res.data.records;
                    console.log("Got "+records.length+" records");
                    if (records) {
                        that.setState({records: records, loading: false }, function() {
                            util.printTimestampsNow();
                            that.refreshChart();
                        });
                    }
                } else that.setState({loading: false});
            });
        }
    }
    refreshChart() {
        if (this._vis_column() && this.refs.chart) {
            this.refs.chart.fullInitialize();
        }
    }
    changeColumn(col) {
        this.update_params({
            col: col
        });
    }
    changeListColumns(cols) {
        this.update_params({
            listcols: cols
        });
    }
    changeDownsample(ds) {
        this.update_params({
            ds: ds
        });
    }
    update_params(_query) {
        var query = this.props.location.query;
        util.mergeObject(query, _query);
        this.props.history.replaceState(null, `/app/data/${this.props.params.sensorKn}`, query);
    }
    changeWindow(start_end, date_or_time, null_e, date_obj) {
        var values = {};
        var param_prop;
        if (start_end == 'start') {
            var current_date = this._start_date();
            param_prop = 'sta';
        } else if (start_end == 'end') {
            var current_date = this._end_date();
            param_prop = 'end';
        }
        // Adjust date or time
        if (date_or_time == 'time' || date_or_time == 'both') {
            current_date.setHours(date_obj.getHours());
            current_date.setMinutes(date_obj.getMinutes());
        }
        if (date_or_time == 'date' || date_or_time == 'both') {
            current_date.setFullYear(date_obj.getFullYear());
            current_date.setMonth(date_obj.getMonth());
            current_date.setDate(date_obj.getDate());
        }
        values[param_prop] = current_date.getTime(); // ms
        this.update_params(values);
    }
    edit_window_from_record(start_end) {
        var record = this.state.selected_record;
        if (record) {
            this.changeWindow(start_end, 'both', null, new Date(record.ts));
        }
        this.toggle_datapoint_dlg();
        this.fetchData();
    }
    show_record_actions(r) {
        var that = this;
        this.setState({selected_record: r}, function() {
            that.toggle_datapoint_dlg()
        });
    }

    goto_record_detail(r) {
      var params = {
        sensorKn: this.props.params.sensorKn
      };
      this.props.history.pushState(null, `/app/data/${params.sensorKn}/record/${r.kn}`);
    }

    handle_export_request() {
        console.log("Export...")
        var cols = this._list_columns();
        var viz_col = this._vis_column();
        if (viz_col != null && cols.indexOf(viz_col) == -1) cols.push(viz_col);
        var specs = {
            ts_start: this._ts_start(),
            ts_end: this._ts_end(),
            columns: cols
        };
        var data = {
            type: 1, // Sensor Data
            target: this.state.sensor.key,
            specs_json: JSON.stringify(specs)
        }
        $.post("/api/report/generate", data, function(res) {
            if (res.success) {
                toastr.success(res.message);
            } else toastr.error(res.message);
        }, 'json');
    }

    toggle_datapoint_dlg() {
        this.setState({datapoint_dlg_open: !this.state.datapoint_dlg_open});
    }

    render() {
        var detail;
        var s = this.state.sensor;
        var schema = this.getSchema();
        var _data = [];
        var prior_ts;
        var ds = this._downsample();
        var gap_cutoff_ms;
        if (ds == AppConstants.DOWNSAMPLE_MIN) gap_cutoff_ms = 1000*60*5; // 5 mins
        else if (ds == AppConstants.DOWNSAMPLE_TEN_MIN) gap_cutoff_ms = 1000*60*50; // 50 mins
        else if (ds == AppConstants.DOWNSAMPLE_HOUR) gap_cutoff_ms = 1000*60*60*5; // 5 hours
        else gap_cutoff_ms = AppConstants.GAP_MINIMUM_SECS * 1000;
        this.state.records.forEach(function(r, i, arr) {
            var _cols = [];
            this._list_columns().map(function(colname, j, arr2) {
                _cols.push(<span title={colname}>{ r.columns[colname] }</span>)
            });
            if (prior_ts != null) {
                var since_prior = Math.abs(r.ts - prior_ts);
                if (since_prior > gap_cutoff_ms) {
                    var gap_text = moment.duration(since_prior).humanize();
                    _data.push(<li className="gap"><i className="fa fa-clock-o"></i> { gap_text }</li>)
                }
            }
            prior_ts = r.ts;

            _data.push(
                <li key={"r"+i} className="list-group-item">
                    <a href="javascript:void(0)" className="title" data-ts={r.ts} onClick={this.goto_record_detail.bind(this, r)}></a>&nbsp;
                    <a href="javascript:void(0)" onClick={this.show_record_actions.bind(this, r)}><i className="fa fa-compress" /></a>
                     <span className="sub">{ util.printDate(r.ts, true) }</span>
                    { _cols }
                </li>
            );
        }, this);
        var _columns = [];
        for (var colname in schema) {
            if (schema.hasOwnProperty(colname)) {
                var label = schema[colname].label || colname;
                _columns.push({ value:colname, label: label });
            }
        }
        var _downsamples = AppConstants.DOWNSAMPLES;
        var _visualization;
        var colname = this._vis_column();
        var listcols = this._list_columns();
        var downsample = this._downsample();
        if (s && colname) {
            var colspec = schema[colname];
            var type = colspec.type || 'number';
            var label = colspec.label || colname;
            if (colspec.unit) label += " ("+colspec.unit+")"
            if (type == 'latlng') {
                // Draw map
                var markers = this.state.records.map(function(r, i, arr) {
                    return {
                        location: r.columns[colname],
                        label: util.printDate(r.ts)
                    };
                });
                _visualization = (
                    <EntityMap entities={markers} addClass="map" />
                    );
            } else {
                var chartColumns = [
                    ['datetime', 'Date', 'date'],
                    [type, label, colname]
                ]
                var chartData = this.state.records.map(function(r, i, arr) {
                    var value = util.type_check(r.columns[colname], type);
                    return [new Date(r.ts), value];
                });
                if (chartColumns.length > 0 && chartData.length > 0) _visualization = (
                    <GChart title={label} columns={chartColumns} data={chartData} ref="chart" />
                )
            }
        }
        var _advanced_items = [
          <MenuItem primaryText="Export" value="export" onClick={this.handle_export_request.bind(this)} />
          ];

        return (
            <div>

                <Dialog title="Data point actions" open={this.state.datapoint_dlg_open} onRequestClose={this.toggle_datapoint_dlg.bind(this)}>
                    <p>Adjust time window</p>
                    <FlatButton label="Start window here" onClick={this.edit_window_from_record.bind(this, 'start')} />
                    Or
                    <FlatButton label="End window here" onClick={this.edit_window_from_record.bind(this, 'end')} />
                </Dialog>

                <h1>Data Viewer <small>{ s ? s.name : "--" }</small></h1>

                <div className="well">
                    <div className="row">
                        <div className="col-sm-6">
                            <label>Visualize Column</label>
                            <Select
                                simpleValue
                                value={colname}
                                options={_columns}
                                onChange={this.changeColumn.bind(this)}
                            />

                            <label>List Data</label>
                            <Select
                                simpleValue
                                value={listcols}
                                options={_columns}
                                onChange={this.changeListColumns.bind(this)}
                                multi={true}
                            />

                            <label>Granularity (downsample)</label>
                            <Select
                                simpleValue
                                value={downsample}
                                options={_downsamples}
                                onChange={this.changeDownsample.bind(this)}
                            />
                        </div>
                        <div className="col-sm-6">
                            <label>Start</label>
                            <DatePicker onChange={this.changeWindow.bind(this, 'start', 'date')} value={this._start_date()} autoOk={true} />
                            <TimePicker format='24hr' onChange={this.changeWindow.bind(this, 'start', 'time')} value={this._start_date()} autoOk={true} />
                            <label>End</label>
                            <DatePicker onChange={this.changeWindow.bind(this, 'end', 'date')} value={this._end_date()} autoOk={true} />
                            <TimePicker format='24hr' onChange={this.changeWindow.bind(this, 'end', 'time')} value={this._end_date()} autoOk={true} />

                            <br/>
                            <FlatButton secondary={true} onClick={this.fetchData.bind(this)} label="Update" />
                            <IconMenu iconButtonElement={ <FlatButton label="Advanced" /> }>
                              { _advanced_items }
                            </IconMenu>

                        </div>

                    </div>
                </div>

                { _visualization }

                <LoadStatus loading={this.state.loading} empty={this.state.records.length == 0}/>

                <ul className="list-group">
                { _data }
                </ul>

            </div>
        );
    }
}
