var React = require('react');
var Router = require('react-router');
var $ = require('jquery');
var DialogChooser = require('components/DialogChooser');
var LoadStatus = require('components/LoadStatus');
var AppConstants = require('constants/AppConstants');
var RuleStore = require('stores/RuleStore');
var RuleActions = require('actions/RuleActions');
var mui = require('material-ui');
var RefreshIndicator = mui.RefreshIndicator;
var RaisedButton = mui.RaisedButton;
var FlatButton = mui.FlatButton;
var IconButton = mui.IconButton;
var DatePicker = mui.DatePicker;
var TimePicker = mui.TimePicker;
var api = require('utils/api');
var util = require('utils/util');
var toastr = require('toastr');
var bootbox = require('bootbox');
var Select = require('react-select');
import connectToStores from 'alt/utils/connectToStores';
import {changeHandler} from 'utils/component-utils';
import history from 'config/history'

var Link = Router.Link;

@connectToStores
@changeHandler
export default class AlarmViewer extends React.Component {
  static defaultProps = {}
  constructor(props) {
    super(props);
    var now = util.nowTimestamp();
    this.state = {
      alarms: [],
      filters: {
        ts_start: new Date(now - 1000*60*60*24), // 24 hrs ago
        ts_end: new Date(now),
        rule_id: null
      }
    };
  }

  static getStores() {
    return [RuleStore];
  }
  static getPropsFromStores() {
    var st = RuleStore.getState();
    return st;
  }

  componentWillReceiveProps(nextProps) {
  }

  componentDidUpdate(prevProps, prevState) {
  }

  componentDidMount() {
    this.fetch_alarms();
    RuleStore.get_rules();
  }

  fetch_alarms(skn) {
    var sensor_kn = this.props.params.sensorKn;
    var { filters } = this.state;
    if (sensor_kn) {
      this.setState({loading: true, alarms: []}, () => {
        var data = {
          'rule_id': filters.rule_id,
          'sensor_kn': sensor_kn,
          'ts_start': filters.ts_start.getTime(),
          'ts_end': filters.ts_end.getTime()
        };
        api.get("/api/alarm", data, (res) => {
          this.setState({
            alarms: res.data.alarms,
            loading: false
          }, function() {
            util.printTimestampsNow(null, null, null, "UTC");
          });
        });
      });
    }
  }

  changeWindow(start_end, date_or_time, null_e, date_obj) {
      var values = {};
      var {filters} = this.state;
      var param_prop;
      if (start_end == 'start') {
          var current_date = this._start_date();
          param_prop = 'ts_start';
      } else if (start_end == 'end') {
          var current_date = this._end_date();
          param_prop = 'ts_end';
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
      filters[param_prop] = current_date;
      this.setState({filters: filters});
  }

  _start_date() {
    return new Date(this.state.filters.ts_start);
  }

  _end_date() {
    return new Date(this.state.filters.ts_end);
  }

  render() {
    var {sensorKn} = this.props.params;
    var {alarms, loading, filters} = this.state;
    var content, _filters;
      var rule_opts = util.flattenDict(this.props.rules).map((r) => {
        return { value: r.id, label: r.name };
      });
    var _filters = (
      <div className="well">
        <div className="row">
          <div className="col-sm-6">
            <label>Start</label>
            <DatePicker onChange={this.changeWindow.bind(this, 'start', 'date')} value={this._start_date()} autoOk={true} />
            <TimePicker format='24hr' onChange={this.changeWindow.bind(this, 'start', 'time')} value={this._start_date()} autoOk={true} />
          </div>
          <div className="col-sm-6">
            <label>End</label>
            <DatePicker onChange={this.changeWindow.bind(this, 'end', 'date')} value={this._end_date()} autoOk={true} />
            <TimePicker format='24hr' onChange={this.changeWindow.bind(this, 'end', 'time')} value={this._end_date()} autoOk={true} />
          </div>
        </div>
        <div className="row">
          <div className="col-sm-6">
            <label>Rule Filter</label>
            <Select value={filters.rule_id} options={rule_opts} onChange={this.changeHandlerVal.bind(this, 'filters', 'rule_id')} simpleValue />
          </div>
          <div className="col-sm-6">
            <FlatButton secondary={true} onClick={this.fetch_alarms.bind(this)} label="Refresh" />
          </div>
        </div>
      </div>
    );
    if (loading) {
      content = (<RefreshIndicator size={40} left={50} top={50} status="loading" />);
    } else {
      var n_alarms = alarms.length;
      var _alarms = alarms.map((a, i, arr) => {
        return <li className="list-group-item" key={i}>
          <span className="title">{ a.rule_name }</span>
          <span className="sub" data-ts={a.ts_start}></span>
        </li>
      });
      content = (
        <div>

          <ul className="list-group">
            { _alarms }
          </ul>

          <small><b>{ n_alarms }</b> alarm(s) in window</small>

        </div>
      );
    }
    return (
      <div className="AlarmViewer">
        <h1><i className="fa fa-warning"></i> Alarm Viewer ( { sensorKn } )</h1>

        { _filters }
        { content }

      </div>
      );
  }
}
