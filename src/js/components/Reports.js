'use strict';

var React = require('react');
var Router = require('react-router');

var EntityMap = require('components/EntityMap');
var SensorDetail = require('components/SensorDetail');
var $ = require('jquery');
var AppConstants = require('constants/AppConstants');
var util = require('utils/util');
var api = require('utils/api');
var mapc = require('utils/map_common');
var RouteHandler = Router.RouteHandler;
var FetchedList = require('components/FetchedList');
var api = require('utils/api');
var toastr = require('toastr');
var mui = require('material-ui'),
  FlatButton = mui.FlatButton,
  RaisedButton = mui.RaisedButton,
  FontIcon = mui.FontIcon,
  DatePicker = mui.DatePicker,
  TimePicker = mui.TimePicker,
  IconMenu = mui.IconMenu,
  TextField = mui.TextField,
  MenuItem = mui.MenuItem;

var SensorTypeActions = require('actions/SensorTypeActions');
var SensorTypeStore = require('stores/SensorTypeStore');

import {Tabs, Tab} from 'material-ui/Tabs';
import connectToStores from 'alt/utils/connectToStores';
import {changeHandler} from 'utils/component-utils';
import {removeItemsById} from 'utils/store-utils';
var Select = require('react-select');
import {clone} from 'lodash';

var Link = Router.Link;

@connectToStores
@changeHandler
export default class Reports extends React.Component {
  static defaultProps = { user: null };

  constructor(props) {
    super(props);
    this.state = {
      form: {},
      loading: false
    };
  }

  static getStores() {
    return [SensorTypeStore];
  }
  static getPropsFromStores() {
    var st = SensorTypeStore.getState();
    return st;
  }

  componentDidMount() {
    this.fetchReports();
    SensorTypeActions.get_sensor_types(); // Fetch if not in store
  }

  componentDidUpdate(prevProps, prevState) {
    var detailOpenClose = (prevProps.params.sensorKn == null) != (this.props.params.sensorKn == null);
    if (detailOpenClose) this.refs.map.resize();
  }
  fetchReports() {
    var that = this;
    this.setState({loading: true});
    var data = {
    };
    api.get("/api/report", data, function(res) {
      if (res.success) {
        var reports = res.data.reports;
        that.setState({reports: reports, loading: false });
      } else that.setState({loading: false});
    });
  }
  generate_report(type_int) {
    var specs = clone(this.state.form);
    if (specs.start) specs.start = specs.start.getTime();
    if (specs.end) specs.end = specs.end.getTime();
    var data = {
        type: type_int,
        specs_json: JSON.stringify(specs)
    }
    api.post("/api/report/generate", data, function(res) {
    })
  }

  delete(r) {
    api.post("/api/report/delete", {rkey: r.key}, (res) => {
      this.refs.list.remove_item_by_key(r.key, 'key');
    });
  }

  download(r) {
    if (r.serve_url) window.open(r.serve_url,'_blank');
  }

  renderReport(r) {
    var _download;
    if (r.status == AppConstants.REPORT_DONE) _download = <a href="javascript:void(0)" onClick={this.download.bind(this, r)}>Download</a>;
    var status_text = util.findItemById(AppConstants.REPORT_STATUSES, r.status, 'value').label;
    return (
      <li className="list-group-item">
        <span className="title">{ r.title }</span>
        <span className="sub">{ status_text }</span>
        { _download }
        &nbsp;<a href="javascript:void(0)" onClick={this.delete.bind(this, r)}><i className="fa fa-trash"></i></a>
        <span className="sub right" data-ts={r.ts_created}></span>
      </li>
      )
  }

  render() {
    var form = this.state.form;
    var sensortype_opts = util.flattenDict(this.props.sensor_types).map((st) => {
      return {value: st.id, label: st.name};
    });
    return (
      <div>
        <h1>Reports</h1>

        <FetchedList ref="list" url="/api/report" listProp="reports" renderItem={this.renderReport.bind(this)} autofetch={true}/>

        <h2>Generate Report</h2>
        <Tabs>
          <Tab label="Records">

            <br/>
            <div className="alert alert-info">Generate a report of all raw records for all sensors. To generate a report
            for a particular sensor, go to the data viewer and choose 'export'</div>

            <div className="row">
              <div className="col-sm-6">
                <DatePicker onChange={this.changeHandlerNilVal.bind(this, 'form', 'start')} value={form.start} autoOk={true} hintText="From" />
              </div>
              <div className="col-sm-6">
                <DatePicker onChange={this.changeHandlerNilVal.bind(this, 'form', 'end')} value={form.end} autoOk={true} hintText="End" />
              </div>
            </div>

            <div className="row">
              <div className="col-sm-6">
                <TextField hint="Columns" floatingLabelText="Columns (comma separated)" onChange={this.changeHandler.bind(this, 'form', 'columns')} value={form.columns} />
              </div>
              <div className="col-sm-6">
                <label>Sensor Type (optional)</label>
                <Select options={sensortype_opts} onChange={this.changeHandlerVal.bind(this, 'form', 'sensortype_id')} value={form.sensortype_id} simpleValue />
              </div>
            </div>

            <RaisedButton label="Generate" primary={true} icon={<FontIcon className="material-icons">play_circle_filled</FontIcon>} onClick={this.generate_report.bind(this, 1)} />
          </Tab>

          <Tab label="Alarms">

            <div className="row">
              <div className="col-sm-6">
                <DatePicker onChange={this.changeHandlerNilVal.bind(this, 'form', 'start')} value={form.start} autoOk={true} hintText="From" />
              </div>
              <div className="col-sm-6">
                <DatePicker onChange={this.changeHandlerNilVal.bind(this, 'form', 'end')} value={form.end} autoOk={true} hintText="End" />
              </div>
            </div>

            <div className="row">
              <div className="col-sm-6">
              </div>
            </div>

            <FlatButton label="Generate" onClick={this.generate_report.bind(this, 2)} />
          </Tab>

          <Tab label="Analyses">

            <div className="row">
              <div className="col-sm-6">
                <DatePicker onChange={this.changeHandlerNilVal.bind(this, 'form', 'start')} value={form.start} autoOk={true} hintText="From" />
              </div>
              <div className="col-sm-6">
                <DatePicker onChange={this.changeHandlerNilVal.bind(this, 'form', 'end')} value={form.end} autoOk={true} hintText="End" />
              </div>
            </div>
            <div className="row">
              <div className="col-sm-6">
                <label>Sensor Type (optional)</label>
                <Select options={sensortype_opts} onChange={this.changeHandlerVal.bind(this, 'form', 'sensortype_id')} value={form.sensortype_id} simpleValue />
              </div>
              <div className="col-sm-6">
                <TextField hint="Columns" floatingLabelText="Columns (comma separated)" onChange={this.changeHandler.bind(this, 'form', 'columns')} value={form.columns} />
              </div>
            </div>
            <FlatButton label="Generate" onClick={this.generate_report.bind(this, 3)} />
          </Tab>

          <Tab label="API Logs">

            <div className="row">
              <div className="col-sm-6">
                <DatePicker onChange={this.changeHandlerNilVal.bind(this, 'form', 'start')} value={form.start} autoOk={true} hintText="From" />
              </div>
              <div className="col-sm-6">
                <DatePicker onChange={this.changeHandlerNilVal.bind(this, 'form', 'end')} value={form.end} autoOk={true} hintText="End" />
              </div>
            </div>

            <div className="row">
              <div className="col-sm-6">
              </div>
            </div>

            <FlatButton label="Generate" onClick={this.generate_report.bind(this, 4)} />
          </Tab>

        </Tabs>
      </div>
    );
  }
};
