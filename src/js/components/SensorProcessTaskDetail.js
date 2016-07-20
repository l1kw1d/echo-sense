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
var Dialog = mui.Dialog;
var IconButton = mui.IconButton;
var util = require('utils/util');
var toastr = require('toastr');
var bootbox = require('bootbox');
var api = require('utils/api');
import history from 'config/history'

var Link = Router.Link;

export default class SensorProcessTaskDetail extends React.Component {
  static defaultProps = {}

  constructor(props) {
    super(props);
    this.state = {
      spt: null
    };
  }

  componentWillReceiveProps(nextProps) {
    var new_data = nextProps.params.processtaskKn && (!this.props.params.processtaskKn || nextProps.params.processtaskKn != this.props.params.processtaskKn);
    if (new_data) {
      this.fetchData(nextProps.params.processtaskKn);
    }
  }

  componentDidUpdate(prevProps, prevState) {
  }

  componentDidMount() {
    if (this.props.params.processtaskKn != null) {
      this.fetchData();
    }
  }

  handle_close() {
    var skn = this.props.params.sensorKn;
    history.push(`/app/sensors/${skn}`);
  }

  fetchData(kn) {
    var kn = kn || this.props.params.processtaskKn;
    var sensorKn = this.props.params.sensorKn;
    console.log(kn);
    if (kn != null) {
      api.get("/api/sensorprocesstask/"+kn, {}, (res) => {
        console.log(res.data.spt);
        this.setState({
          spt: res.data.spt,
          loading: false
        });
      });
    }
  }

  render() {
    var spt = this.state.spt;
    var content;
    if (!spt) {
      content = (<RefreshIndicator size={40} left={50} top={50} status="loading" />);
    } else {
      var status_icon = <i className={AppConstants.PROCESS_STATUS_ICONS[spt.status_last_run]}/>
      content = (
        <Dialog open={true} onRequestClose={this.handle_close.bind(this)}>
          <div>
            <h1><i className="fa fa-cog"></i> { spt.label }</h1>
            <div>
              <b>Task Label:</b> { spt.process_task_label }<br/>
            </div>

            <div className="well">
              <h3>Last Run</h3>
              <b>Last Run Start:</b> <span data-ts={spt.ts_last_run_start}></span><br/>
              <b>Last Run Finish:</b> <span data-ts={spt.ts_last_run}></span><br/>
              <b>Last Record:</b> <span data-ts={spt.ts_last_record}></span><br/>
              <b>Running:</b> <span>{ spt.running ? "Yes" : "No" }</span><br/>
              <b>Status:</b> { status_icon } { AppConstants.PROCESS_STATUS_LABELS[spt.status_last_run] }<br/>
              <b>Narrative:</b> { spt.narrative_last_run || "--" }<br/>
            </div>

          </div>
        </Dialog>
      );
    }
    return content;
  }
}

SensorProcessTaskDetail.contextTypes = {
  router: React.PropTypes.func
};

