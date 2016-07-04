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
var FetchedList = require('components/FetchedList');
var util = require('utils/util');
var toastr = require('toastr');
var bootbox = require('bootbox');
var UserStore = require('stores/UserStore');
var IconMenu = mui.IconMenu;
var FontIcon = mui.FontIcon;
var MenuItem = mui.MenuItem;
var TargetStore = require('stores/TargetStore');
var TargetActions = require('actions/TargetActions');
var api = require('utils/api');
import connectToStores from 'alt/utils/connectToStores';
import history from 'config/history'

var Link = Router.Link;

@connectToStores
export default class TargetDetail extends React.Component {

  static defaultProps = { user: null };
  constructor(props) {
    super(props);
    this.state = {
      target: null,
      loading: false
    };
  }
  static getStores() {
    return [UserStore];
  }
  static getPropsFromStores() {
    var st = UserStore.getState();
    return st;
  }

  componentWillReceiveProps(nextProps) {
    var newTarget = nextProps.params.targetID && (!this.props.params.targetID || nextProps.params.targetID != this.props.params.targetID);
    if (newTarget) {
      this.prepareTarget(nextProps.params.targetID);
    }
  }

  componentDidMount() {
    if (this.props.params.targetID) {
      this.prepareTarget(this.props.params.targetID);
    }
  }

  prepareTarget(id) {
    this.fetchData(id);
  }

  fetchData(_tid) {
    var that = this;
    var tid = _tid || this.props.params.targetID;
    if (tid) {
      this.setState({loading: true, sensor: null});
      api.get("/api/target/"+tid, {}, function(res) {
        if (res.success) {
          that.setState({
            target: res.data.target,
            loading: false
          }, function() {
            util.printTimestampsNow(null, null, null, "UTC");
          });
        } else that.setState({loading:false});
      });
    }
  }

  close() {
    if (this.props.onClose) this.props.onClose();
  }

  confirm_delete() {
    bootbox.confirm("Really delete?", (ok) => {
      if (ok) {
        var t = this.state.target;
        TargetActions.delete(t.key);
        this.props.history.push("/app/targets");
      }
    });
  }

  gotoSensor(s) {
    history.pushState(null, `/app/sensors/${s.kn}`);
  }

  userAdmin() {
    return this.props.user && this.props.user.level == 4;
  }

  render() {
    var t = this.state.target;
    var user = this.props.user;
    var can_write = user ? user.level > AppConstants.USER_READ : false;
    var content;
    if (!t) {
      content = (<RefreshIndicator size={40} left={50} top={50} status="loading" />);
    } else {
      var _action_items = [];
      content = (
        <div>
          <Link to="/app/targets" className='close'><i className="fa fa-close"></i></Link>
          <div className="pull-right">
            <IconMenu iconButtonElement={<IconButton><FontIcon className="material-icons">more_vert</FontIcon> /></IconButton>}>
              <MenuItem primaryText="Delete" onClick={this.confirm_delete.bind(this)} leftIcon={<FontIcon className="material-icons">delete</FontIcon>} />
            </IconMenu>
          </div>
          <h2><i className="fa fa-th-large"/> { t.name } <IconButton iconClassName="fa fa-refresh" tooltip="Refresh" onClick={this.fetchData.bind(this, null)}/></h2>
          <div className="row">
            <div className="col-sm-6">
              <small>
                <b>Created:</b> <span data-ts={t.ts_created}></span><br/>
                <b>Updated:</b> <span data-ts={t.ts_updated}></span><br/>
              </small>
            </div>
            <div className="col-sm-6">
              <div hidden={_action_items.length == 0}>
                <IconMenu iconButtonElement={ <FlatButton label="Actions" /> }>
                  { _action_items }
                </IconMenu>
              </div>
            </div>
          </div>

          <div>
            <h2>Sensors</h2>
            <FetchedList url="/api/sensor" params={{target_id: t.id}} autofetch={true} listProp="sensors" labelProp="name" onItemClick={this.gotoSensor.bind(this)} />
          </div>

        </div>
      );
    }
    return (
      <div className="detailBox">
        { content }
      </div>
      );
  }
}
