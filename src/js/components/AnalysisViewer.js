var React = require('react');
var Router = require('react-router');
var Link = Router.Link;
var $ = require('jquery');
var util = require('../utils/util');
var LoadStatus = require('./LoadStatus');
var EntityMap = require('./EntityMap');
var api = require('utils/api');
var GChart = require('./GChart');
var moment = require('moment');
var SensorTypeActions = require('actions/SensorTypeActions');
var SensorTypeStore = require('stores/SensorTypeStore');
var SensorActions = require('actions/SensorActions');
var SensorStore = require('stores/SensorStore');
var Select = require('react-select');
var mui = require('material-ui');
var FlatButton = mui.FlatButton;
var Dialog = mui.Dialog;
var AutoComplete = mui.AutoComplete;
var RaisedButton = mui.RaisedButton;
var AppConstants = require('../constants/AppConstants');
var IconMenu = mui.IconMenu;
var MenuItem = mui.MenuItem;
var toastr = require('toastr');
var FontIcon = mui.FontIcon;
import {merge} from 'lodash';
import {changeHandler} from 'utils/component-utils';
import connectToStores from 'alt/utils/connectToStores';

@connectToStores
@changeHandler
export default class AnalysisViewer extends React.Component {
    static defaultProps = { user: null };

    constructor(props) {
        super(props);
        this.MIN_CHART_DURATION = 1000*60*5; // 5 minutes
        this.state = {
            analyses: [],
            loading: false,
            suggested_columns: [],
            select_listener_handle: null,
            selected_analysis: null,
            form: {
                limit: 50,
                chart_type: "Timeline",
                col: null
            }
        };
        this.HINTS = {
            "Timeline": "The timeline below shows sensors in rows, and bars indicate individual " +
                "analysis objects. Bars span from the date of creation to the date of last update.",
            "ScatterChart": "The chart below shows analysis objects as points. Sensors are grouped " +
                "as series of the same color."
        }
    }

    static getStores() {
        return [SensorTypeStore, SensorStore];
    }
    static getPropsFromStores() {
        var st = SensorTypeStore.getState();
        merge(st, SensorStore.getState());
        return st;
    }

    componentDidMount() {
        if (Object.keys(this.props.sensor_types).length == 0) SensorTypeActions.fetchTypes();
    }

    componentWillReceiveProps(nextProps) {
    }

    componentDidUpdate(prevProps, prevState) {
        var form = this.state.form;
        var chart_type_change = form.chart_type != prevState.form.chart_type;
        if (chart_type_change) {
            this.refreshChart();
        }
    }

    fetchData() {
        var form = this.state.form;
        var that = this;
        var skn = this.props.location.query.skn;
        this.refreshChart();
        if (form.sensortype_id || skn) {
            this.setState({loading: true});
            var data = {
                'sensortype_id': form.sensortype_id,
                'with_props': 1,
                'max': form.limit,
            };
            if (skn) data['sensor_kn'] = skn;
            api.get("/api/analysis", data, function(res) {
                if (res.success) {
                    var analyses = res.data.analyses;
                    console.log("Got "+analyses.length+" analyses");
                    var suggested_columns = [];
                    var sensor_key_names = [];
                    if (analyses.length > 0) {
                        for (var i=0; i<10 && i<analyses.length; i++) {
                            var a = analyses[i];
                            var cols = a.columns;
                            var colnames = Object.keys(cols);
                            if (sensor_key_names.indexOf(a.sensor_kn) == -1) sensor_key_names.push(a.sensor_kn);
                            colnames.forEach(function(colname) {
                                if (suggested_columns.indexOf(colname) == -1) {
                                    suggested_columns.push(colname);
                                }
                            });
                        }
                    }
                    if (form.chart_type == 'ScatterChart' && !form.col) {
                        toastr.info("Select a column to chart analysis values")
                    }
                    that.setState({analyses: analyses, loading: false, suggested_columns: suggested_columns }, function() {
                        SensorActions.get_sensors_by_key_names(sensor_key_names);
                    });
                } else that.setState({loading: false});
            });
        }
    }

    refreshChart() {
        if (this.refs.chart != null) this.refs.chart.fullInitialize();
    }

    _column() {
        return this.props.location.query.col;
    }

    handle_chart_drawn() {
        var chart = this.refs.chart.getChart();
        if (chart) {
            if (this.state.select_listener_handle) {
                google.visualization.events.removeListener(this.state.select_listener_handle);
            }
            var select_listener_handle = google.visualization.events.addListener(chart, 'select', this.handle_chart_select.bind(this));
            this.setState({select_listener_handle: select_listener_handle});
        }
    }

    handle_chart_select() {
        var chart = this.refs.chart.getChart();
        if (chart) {
            var sel = chart.getSelection();
            if (sel.length == 1) {
                var row_index = sel[0].row;
                var a = this.state.analyses[row_index];
                this.setState({selected_analysis: a});
            }
        }
    }

    clear_analysis_selection() {
        this.setState({selected_analysis: null});
    }

    render() {
        var _visualization;
        var form = this.state.form;
        var analyses = this.state.analyses;
        var skn = this.props.location.query.skn;
        if (analyses.length > 0) {
            var chartColumns = [];
            if (form.chart_type == 'Timeline') {
                chartColumns = [
                    {type: 'string', label: 'Sensor Key', id: 'sensor'},
                    {type: 'string', label: 'Value', id: 'value'},
                    {type: 'string', role: 'tooltip'},
                    {type: 'date', label: 'Start', id: 'Start'},
                    {type: 'date', label: 'End', id: 'End'}
                ];
            } else if (form.chart_type == 'ScatterChart') {
                chartColumns = [
                    {type: 'date', label: 'Start', id: 'Start'},
                    {type: 'number', label: form.col || "Value", id: 'value'},
                    {type: 'string', role: 'style'},
                    {type: 'string', role: 'tooltip'}
                ];
            }
            var chartData = this.state.analyses.map((a, i, arr) => {
                var value = null;
                if (form.col) {
                    var colval = a.columns[form.col];
                    if (colval) value = colval.toString();
                }
                var start = new Date(a.ts_created);
                var ts_updated = a.ts_updated;
                // Google viz can't handle same start/end
                if (ts_updated == null || (ts_updated - a.ts_created) < this.MIN_CHART_DURATION) ts_updated = ts_updated + this.MIN_CHART_DURATION;
                var end = new Date(ts_updated);
                var tooltip = a.kn;
                var sensor_label = a.sensor_kn;
                var s = this.props.sensors[a.sensor_kn];
                if (s) sensor_label = s.name;
                var row = [];
                if (form.chart_type == "Timeline") row = [sensor_label, value || "--", tooltip, start, end];
                else if (form.chart_type == "ScatterChart") {
                    var color = util.stringToColor(a.sensor_kn);
                    var point_style = 'point { fill-color: '+color+'; }';
                    tooltip += " (Sensor: "+sensor_label+")";
                    row = [start, value ? parseFloat(value) : 0, point_style, tooltip];
                }
                return row;
            });
            var opts = {tooltip: {isHtml: true}};
            var hint = this.HINTS[form.chart_type];
            _visualization = (
                <div>
                    <p>{ hint}</p>
                    <GChart title="Analysis Timeline" columns={chartColumns} data={chartData}
                        ref="chart" type={form.chart_type} height="600"
                        options={opts} afterDraw={this.handle_chart_drawn.bind(this)} />
                </div>
            );
        }

        var _sensor_types = util.flattenDict(this.props.sensor_types).map(function(st) {
            return { value: st.id, label: st.name };
        });

        var _limits = [
            { value: 10, label: 10 },
            { value: 50, label: 50 },
            { value: 150, label: 150 }
        ];

        var chart_types = [
            { value: 'Timeline', label: "Timeline" },
            { value: 'ScatterChart', label: "Scatter" },
        ];

        var selected_analysis = this.state.selected_analysis;
        var _dialog_content;
        if (selected_analysis) _dialog_content = (
            <div>
                <Link to={`/app/sensors/${selected_analysis.sensor_kn}`}><FlatButton label="Goto Sensor" /></Link>
                <Link to={`/app/analysis/${selected_analysis.kn}`}><FlatButton label="Goto Analysis" /></Link>
            </div>
        );
        return (
            <div>

                <h2>Viewer</h2>

                <div className="well">
                    <div className="row">
                        <div className="col-sm-6">

                            <div className="form-group" hidden={skn==null}>
                                <label>Sensor</label><br/>
                                <span>{ skn }</span>
                            </div>

                            <div className="form-group" hidden={skn!=null}>
                                <label>Sensor Type</label>
                                <Select
                                    simpleValue
                                    value={form.sensortype_id}
                                    options={_sensor_types}
                                    onChange={this.changeHandlerVal.bind(this, 'form', 'sensortype_id')} />
                            </div>

                            <div className="form-group">
                                <label>Limit</label>
                                <Select
                                    simpleValue
                                    value={form.limit}
                                    options={_limits}
                                    onChange={this.changeHandlerVal.bind(this, 'form', 'limit')} />
                            </div>

                            <RaisedButton primary={true} label="Reload" icon={<FontIcon className="material-icons">refresh</FontIcon>} onClick={this.fetchData.bind(this)} />

                        </div>

                        <div className="col-sm-6">

                            <label>Show Column Data</label><br/>
                            <AutoComplete
                                hintText="Column Data"
                                searchText={form.col}
                                dataSource={this.state.suggested_columns}
                                onNewRequest={this.changeHandlerVal.bind(this, 'form', 'col')}
                                onChange={this.changeHandlerVal.bind(this, 'form', 'col')}
                                onUpdateInput={this.changeHandlerVal.bind(this, 'form', 'col')} />

                            <RaisedButton label="Update" onClick={this.refreshChart.bind(this)} />
                        </div>
                        <div className="col-sm-6">
                            <label>Chart Type</label>
                            <Select
                                simpleValue
                                value={form.chart_type}
                                options={chart_types}
                                onChange={this.changeHandlerVal.bind(this, 'form', 'chart_type')} />
                        </div>

                    </div>
                </div>

                { _visualization }

                <LoadStatus loading={this.state.loading} empty={this.state.analyses.length == 0}/>

                <Dialog open={selected_analysis != null} title={selected_analysis ? selected_analysis.kn : "--"} onRequestClose={this.clear_analysis_selection.bind(this)} >
                    { _dialog_content }
                </Dialog>

            </div>
        );
    }
}
