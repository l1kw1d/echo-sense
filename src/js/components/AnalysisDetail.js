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

export default class AnalysisDetail extends React.Component {
  static defaultProps = {  };
  constructor(props) {
    super(props);
    this.state = {
      analysis: null
    };
  }

  componentWillReceiveProps(nextProps) {
    var newAnalysis = nextProps.params.analysisKn && (!this.props.params.analysisKn || nextProps.params.analysisKn != this.props.params.analysisKn);
    if (newAnalysis) {
      this.fetchAnalysis();
    }
  }
  componentDidUpdate(prevProps, prevState) {
  }
  componentDidMount() {
    this.fetchAnalysis();
  }

  fetchAnalysis() {
    var that = this;
    var kn = this.props.params.analysisKn;
    if (kn) {
      this.setState({loading: true, sensor: null});
      var data = {
        with_props: 1
      };
      $.getJSON(`/api/analysis/${kn}`, data, function(res) {
        if (res.success) {
          that.setState({
            analysis: res.data.analysis,
            loading: false
          }, function() {
            util.printTimestampsNow(null, null, null, "UTC");
          });
        } else that.setState({loading:false});
      }, 'json');
    }
  }

  render() {
    var a = this.state.analysis;
    var sensorKn = this.props.params.sensorKn;
    var content;
    if (!a) {
      content = (<RefreshIndicator size={40} left={50} top={50} status="loading" />);
    } else {
      var _columns = [];
      if (a.columns) {
        for (var colname in a.columns) {
          if (a.columns.hasOwnProperty(colname)) {
            _columns.push(
              <li className="list-group-item"><b>{ colname }</b> { a.columns[colname] }</li>
              )
          }
        }
      }
      content = (
        <div>
          <h1>Analysis - { a.kn }</h1>

          <div>
            <IconButton iconClassName="material-icons" tooltip="Reload" onClick={this.fetchAnalysis.bind(this)}>refresh</IconButton>
          </div>

          <div>
            <b>Created:</b> <span>{ util.printDate(a.ts_created, true) }</span><br/>
            <b>Updated:</b> <span>{ util.printDate(a.ts_updated, true) }</span><br/>
            <b>Sensor:</b> <span><Link to={`/app/sensors/${a.sensor_kn}`}>{ a.sensor_kn }</Link></span>

            <h2>Data Columns</h2>
            <ul className="list-group">
              { _columns }
            </ul>
          </div>

        </div>
      );
    }
    return (
      <div className="analysisDetail">
        { content }
      </div>
      );
  }
}
