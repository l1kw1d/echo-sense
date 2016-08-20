var React = require('react');
var Router = require('react-router');
var $ = require('jquery');
var DialogChooser = require('components/DialogChooser');
var LoadStatus = require('components/LoadStatus');
var AppConstants = require('constants/AppConstants');
var mui = require('material-ui');
var RefreshIndicator = mui.RefreshIndicator;
var RaisedButton = mui.RaisedButton;
var FlatButton = mui.FlatButton;
var IconButton = mui.IconButton;
var util = require('utils/util');
var toastr = require('toastr');
var bootbox = require('bootbox');
import history from 'config/history'

var Link = Router.Link;

export default class RecordDetail extends React.Component {
  static defaultProps = {  };
  constructor(props) {
    super(props);
    this.state = {
      record: null
    };
  }

  componentWillReceiveProps(nextProps) {
    var newRecord = nextProps.params.recordKn && (!this.props.params.recordKn || nextProps.params.recordKn != this.props.params.recordKn);
    if (newRecord) {
      this.fetchRecord();
    }
  }
  componentDidUpdate(prevProps, prevState) {
  }
  componentDidMount() {
    this.fetchRecord();
  }

  fetchRecord() {
    var that = this;
    var kn = this.props.params.recordKn;
    var sensorKn = this.props.params.sensorKn;
    if (kn && sensorKn) {
      this.setState({loading: true, sensor: null});
      var data = {
      };
      $.getJSON("/api/data/"+sensorKn+"/"+kn, data, function(res) {
        if (res.success) {
          that.setState({
            record: res.data.record,
            loading: false
          }, function() {
            util.printTimestampsNow(null, null, null, "UTC");
          });
        } else that.setState({loading:false});
      }, 'json');
    }
  }

  render() {
    var r = this.state.record;
    var sensorKn = this.props.params.sensorKn;
    var content;
    if (!r) {
      content = (<RefreshIndicator size={40} left={50} top={50} status="loading" />);
    } else {
      var _columns = [];
      if (r.columns) {
        for (var colname in r.columns) {
          if (r.columns.hasOwnProperty(colname)) {
            _columns.push(
              <li className="list-group-item"><b>{ colname }</b> { r.columns[colname] }</li>
              )
          }
        }
      }
      content = (
        <div>
          <h1>{ util.printDate(r.ts, true) } ( { sensorKn })</h1>
          <div>
            <b>Recorded:</b> <span>{ util.printDate(r.ts, true) }</span><br/>
            <b>Created:</b> <span>{ util.printDate(r.ts_created, true) }</span><br/>
            <b>Sensor:</b> <span><Link to={`/app/sensors/${r.sensor_kn}`}>{ r.sensor_kn }</Link></span>

            <h2>Data</h2>
            <ul className="list-group">
              { _columns }
            </ul>
          </div>

        </div>
      );
    }
    return (
      <div className="datapointDetail">
        { content }
      </div>
      );
  }
}
