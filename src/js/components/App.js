'use strict';

var React = require('react');
var Router = require('react-router');
var util = require('utils/util');
var $ = require('jquery');
var bootstrap = require('bootstrap');
var toastr = require('toastr');
import history from 'config/history'

var mui = require('material-ui'),
  FlatButton = mui.FlatButton,
  IconButton = mui.IconButton;

var AppConstants = require('constants/AppConstants');
var Link = Router.Link;
var RouteHandler = Router.RouteHandler;

var IconMenu = mui.IconMenu;
var MenuItem = mui.MenuItem;

var UserActions = require('actions/UserActions');
var UserStore = require('stores/UserStore');
var SearchWidget = require('components/shared/SearchWidget');
import connectToStores from 'alt/utils/connectToStores';
import {authDecorator} from 'utils/component-utils';

@connectToStores
@authDecorator
export default class App extends React.Component {
  static contextTypes = {
    router: React.PropTypes.func
  }
  static defaultProps = { enterprise: null };
  constructor(props) {
    super(props);
    this.state = {
      search_open: false
    };
    this.iSt = {
      color: '#EEE'
    }
    this.ibSt = {
      margin: '0px'
    }
  }
  static getStores() {
    return [UserStore];
  }
  static getPropsFromStores() {
    var st = UserStore.getState();
    return st;
  }

  componentDidMount() {
    if (!this.props.user) {
      UserActions.logout();
    } else {
      util.startAutomaticTimestamps(this.props.user.timezone, 5);
    }
    $('link[title=app_css]').prop('disabled',false);
  }

  componentWillUnmount() {
    $('link[title=app_css]').prop('disabled',true);
    // TODO: Remove automatic timestamps
  }

  toggle_search(open) {
    this.setState({search_open: open});
  }

  menuSelect(menu, e, value) {
    if (value == "logout" && menu == "user") UserActions.logout();
    else history.replaceState(null, value);
  }

  render() {
    var user = this.props.user;
    var is_admin = user ? user.level == AppConstants.USER_ADMIN : false;
    var is_account_admin = is_admin ? true : (user ? user.level == AppConstants.USER_ACCOUNT_ADMIN : false);
    var can_write = user ? user.level > AppConstants.USER_READ : false;
    var wide = this.props.wide;
    var YEAR = "2015";
    var SITENAME = "Echo Sense";
    if (user) {
      var user_string = user.name || user.email || "User";
      var loc = user.location_text || "Somewhere";
      var user_letter = user_string[0];
      var _avatar = (
        <span className="avatar avatar-sm avatar-centered img-circle" style={{ backgroundImage: "url("+user.avatar_serving_url+")" }}></span>
      );
      return (
        <div>
          <aside className="lnav">
            <nav>
              <div hidden={!is_admin}><Link to="/app/admin/manage"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Admin Manage">settings</IconButton></Link></div>
              <div hidden={!is_account_admin}><Link to="/app/users" title="Users"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Users">people</IconButton></Link></div>
              <div hidden={!can_write}><Link to="/app/manage" title="Manage"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Manage">settings_applications</IconButton></Link></div>
              <div hidden={!can_write}><Link to="/app/logs" title="Logs"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Logs">list</IconButton></Link></div>
              <div ><Link to="/app/sensors"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Sensors">fiber_smart_record</IconButton></Link></div>
              <div ><Link to="/app/targets"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Targets">view_module</IconButton></Link></div>
              <div ><Link to="/app/groups"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Groups">folder</IconButton></Link></div>
              <div ><Link to="/app/processing"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Processing">show_chart</IconButton></Link></div>
              <div hidden={!can_write}><Link to="/app/reports"><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Reports">cloud_download</IconButton></Link></div>
              <div><a href="javascript:void(0)" onClick={this.toggle_search.bind(this, true)}><IconButton iconClassName="material-icons" iconStyle={this.iSt} style={this.ibSt} tooltipPosition="bottom-right" tooltip="Search">search</IconButton></a></div>
            </nav>
          </aside>

          <SearchWidget open={this.state.search_open} onRequestClose={this.toggle_search.bind(this, false)} />

          <div id="container" className="container">
            <header className="topBar row">
              <div className="siteHeader col-sm-6">
                <h1><img src="/images/logos/echo_sense_white_512.png" height="15" style={{verticalAlign: '-8%'}} /> { SITENAME }</h1>
                <h2>{ user.ent_name }</h2>
              </div>
              <div className="userSection col-sm-6">

                <div className="userAvatar row">
                  <div className="col-sm-10">
                    <span className="handle">{ user_string }</span>
                    <span className="location"> { loc }</span>
                  </div>
                  <div className="col-sm-2">
                    <IconMenu iconButtonElement={ _avatar } onChange={this.menuSelect.bind(this, 'user')}>
                      <MenuItem value="/app/profile" primaryText="Profile" />
                      <MenuItem value="logout" primaryText="Sign Out" />
                    </IconMenu>
                  </div>
                </div>

              </div>
            </header>
            <div className="content row">
              {React.cloneElement(this.props.children, {user: this.props.user})}
            </div>
          </div>

        </div>
      )
    } else return <div>Logging out...</div>
  }
}