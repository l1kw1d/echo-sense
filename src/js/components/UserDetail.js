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

export default class UserDetail extends React.Component {
  static defaultProps = {  };
  constructor(props) {
    super(props);
    this.state = {
      user: null
    };
  }

  componentWillReceiveProps(nextProps) {
    var updated = nextProps.params.userID && (!this.props.params.userID || nextProps.params.userID != this.props.params.userID);
    if (updated) {
      this.fetch();
    }
  }
  componentDidUpdate(prevProps, prevState) {
  }
  componentDidMount() {
    this.fetch();
  }

  fetch() {
    var that = this;
    var uid = this.props.params.userID;
    if (uid) {
      this.setState({loading: true, user: null});
      var data = {
        with_props: 1
      };
      $.getJSON(`/api/user/${uid}`, data, function(res) {
        if (res.success) {
          that.setState({
            user: res.data.user,
            loading: false
          }, function() {
            util.printTimestampsNow(null, null, null, "UTC");
          });
        } else that.setState({loading:false});
      }, 'json');
    }
  }

  render() {
    var u = this.state.user;
    var content;
    if (!u) {
      content = (<RefreshIndicator size={40} left={50} top={50} status="loading" />);
    } else {
      content = (
        <div>
          <h1>User - { u.id }</h1>
          <div>
            <b>Name:</b> <span>{ u.name || "" }</span><br/>
            <b>Email:</b> <span>{ u.email || "" }</span><br/>
            <b>Phone:</b> <span>{ u.phone || "" }</span><br/>
            <b>Created:</b> <span>{ util.printDate(u.ts_created, true) }</span><br/>
            <b>GCM Reg ID:</b> <span>{ u.gcm_reg_id }</span>

          </div>

        </div>
      );
    }
    return (
      <div className="userDetail">
        { content }
      </div>
      );
  }
}
