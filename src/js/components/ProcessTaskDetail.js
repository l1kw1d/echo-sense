var React = require('react');
var Router = require('react-router');
var $ = require('jquery');
var DialogChooser = require('components/DialogChooser');
var LoadStatus = require('components/LoadStatus');
var AppConstants = require('constants/AppConstants');
var mui = require('material-ui'),
  RefreshIndicator = mui.RefreshIndicator,
  RaisedButton = mui.RaisedButton,
  FlatButton = mui.FlatButton,
  IconButton = mui.IconButton,
  TextField = mui.TextField,
  IconMenu = mui.IconMenu,
  MenuItem = mui.MenuItem,
  FontIcon = mui.FontIcon;
var FetchedList = require('components/FetchedList');
var util = require('utils/util');
var toastr = require('toastr');
var bootbox = require('bootbox');
var UserStore = require('stores/UserStore');
var ProcessTaskStore = require('stores/ProcessTaskStore');
var ProcessTaskActions = require('actions/ProcessTaskActions');
var RuleStore = require('stores/RuleStore');
var RuleActions = require('actions/RuleActions');
var IconMenu = mui.IconMenu;
var MenuItem = mui.MenuItem;
var api = require('utils/api');
var Select = require('react-select');
import {merge, clone} from 'lodash';
import connectToStores from 'alt/utils/connectToStores';
import history from 'config/history'
import {changeHandler} from 'utils/component-utils';

var Link = Router.Link;

@connectToStores
@changeHandler
export default class ProcessTaskDetail extends React.Component {

  static defaultProps = { user: null };
  constructor(props) {
    super(props);
    this.state = {
      loading: false,
      form: {}
    };
  }
  static getStores() {
    return [UserStore, ProcessTaskStore, RuleStore];
  }
  static getPropsFromStores() {
    var st = UserStore.getState();
    merge(st, RuleStore.getState());
    merge(st, ProcessTaskStore.getState());
    return st;
  }

  componentDidUpdate(prevProps, prevState) {
    var task = this.task();
    var form = this.state.form;
    var newTask = this.props.params.processtaskID && (task && (task.updated_ms > (form.updated_ms || 0) || task.id != form.id));
    if (newTask) {
      this.prepare_task(this.props.params.processtaskID);
    }
  }

  componentDidMount() {
    ProcessTaskActions.fetchTask(this.props.params.processtaskID);
    RuleStore.get_rules();
  }

  prepare_task(id) {
    var task = this.props.tasks[id];
    if (task) {
      var form = clone(task);
      form.spec = JSON.parse(form.spec);
      if (form.spec == null) form.spec = {processers: []};
      this.setState({form: form});
    }
  }

  fetch_task() {
    var tid = this.props.params.processtaskID;
    ProcessTaskActions.fetchTask(tid);
  }

  task() {
    var tid = this.props.params.processtaskID;
    if (tid) return this.props.tasks[tid];
    return null;
  }

  close() {
    if (this.props.onClose) this.props.onClose();
  }

  userAdmin() {
    return this.props.user && this.props.user.level == 4;
  }

  confirm_delete() {
    bootbox.confirm("Really delete?", (ok) => {
      if (ok) {
        var task = this.task();
        ProcessTaskActions.delete(task.key);
        this.props.history.push("/app/processing/settings");
      }
    });
  }

  duplicate() {
    ProcessTaskActions.duplicate(this.state.form.key);
  }

  save() {
    var data = clone(this.state.form);
    if (data.spec) data.spec = JSON.stringify(data.spec);
    if (data.week_days.length > 0) data.week_days = data.week_days.join(',');
    if (data.month_days.length > 0) data.month_days = data.month_days.join(',');
    if (data.rule_ids.length > 0) data.rule_ids = data.rule_ids.join(',');
    ProcessTaskActions.update(data);
  }

  add_processer() {
    var form = this.state.form;
    form.spec.processers.push({});
    this.setState({form: form});
  }

  remove_processer(i) {
    var form = this.state.form;
    form.spec.processers.splice(i, 1);
    this.setState({form: form});
  }

  spec_change(index, prop, e) {
    var val = e.target.value;
    var form = this.state.form;
    var processer = form.spec.processers[index];
    if (processer) {
      processer[prop] = val;
      console.log(prop + " >> " + val);
      this.setState({form: form});
    }
  }

  render() {
    var task = this.task();
    var user = this.props.user;
    var form = this.state.form;
    var can_write = user ? user.level > AppConstants.USER_READ : false;
    var content;
    if (!task) {
      content = (<RefreshIndicator size={40} left={50} top={50} status="loading" />);
    } else {
      var rule_opts = util.flattenDict(this.props.rules).map((r) => {
        return { value: r.id, label: r.name };
      });
      var month_day_opts = [];
      for (var day = 1; day <= 31; day++) {
        month_day_opts.push({value: day, label: day});
      }
      var _processers, _spec_editor;
      if (form.spec != null) {
        var spec = form.spec;
        if (spec != null && spec.processers != null) {
          _processers = spec.processers.map((processer, i) => {
            return (
              <div className="well">
                <div className="row">
                  <div className="col-sm-4">
                    <TextField floatingLabelText="Analysis Key Pattern" value={processer.analysis_key_pattern || ""} onChange={this.spec_change.bind(this, i, 'analysis_key_pattern')} fullWidth />
                  </div>
                  <div className="col-sm-4">
                    <TextField floatingLabelText="Column" value={processer.column || ""} onChange={this.spec_change.bind(this, i, 'column')} fullWidth />
                  </div>
                  <div className="col-sm-4">
                    <IconButton iconClassName="material-icons" onClick={this.remove_processer.bind(this, i)} tooltip="Remove">delete</IconButton>
                  </div>
                  <div className="col-sm-12">
                    <TextField floatingLabelText="Calculation" value={processer.calculation || ""} onChange={this.spec_change.bind(this, i, 'calculation')} fullWidth />
                  </div>
                </div>
              </div>
            )
          });
        }
        var _spec_editor = (
          <div>
            { _processers }
            <FlatButton label="New Processer" onClick={this.add_processer.bind(this)} />
          </div>
          );
      }
      content = (
        <div>
          <Link to="/app/processing/settings" className='close'><i className="fa fa-close"></i></Link>
          <h2>
            Process Task
            <IconButton iconClassName="material-icons" tooltip="Save" onClick={this.save.bind(this)}>save</IconButton>
            <IconButton iconClassName="material-icons" tooltip="Refresh" onClick={this.fetch_task.bind(this)}>refresh</IconButton>
          </h2>

          <div className="pull-right">
            <IconMenu iconButtonElement={<IconButton><FontIcon className="material-icons">more_vert</FontIcon> /></IconButton>}>
              <MenuItem primaryText="Delete" onClick={this.confirm_delete.bind(this)} leftIcon={<FontIcon className="material-icons">delete</FontIcon>} />
              <MenuItem primaryText="Duplicate" onClick={this.duplicate.bind(this)} leftIcon={<FontIcon className="material-icons">content_copy</FontIcon>} />
            </IconMenu>
          </div>

          <small>
            <b>ID:</b> { task.id }<br/>
          </small>

          <div className="row">
            <div className="col-sm-6">
              <TextField name="label" floatingLabelText="Label" value={form.label} fullWidth={true} onChange={this.changeHandler.bind(this, 'form', 'label')} />
            </div>
            <div className="col-sm-6">
              <div className="help-block">Task scheduled to run after an <b>interval</b> second delay each time new data is received.</div>
              <TextField name="interval" floatingLabelText="Interval (seconds)" value={form.interval} fullWidth={true} onChange={this.changeHandler.bind(this, 'form', 'interval')} />
            </div>
          </div>
          <div className="row">
            <div className="col-sm-12">
              <label>Rules</label>
              <Select value={form.rule_ids} multi={true} options={rule_opts} onChange={this.changeHandlerMultiVal.bind(this, 'form', 'rule_ids')} />
            </div>
          </div>
          <div className="row">
            <div className="col-sm-6">
              <label>Days of Month</label>
              <div className="help-block">Task will run if day matches either month day or week day, so either or both must be set. Comma separated list of ints.</div>
              <Select multi={true} value={form.month_days} onChange={this.changeHandlerMultiVal.bind(this, 'form', 'month_days')} options={month_day_opts} />
            </div>
            <div className="col-sm-6">
              <label>Days of Week</label>
              <Select multi={true} value={form.week_days} onChange={this.changeHandlerMultiVal.bind(this, 'form', 'week_days')} options={AppConstants.WEEKDAYS} />
            </div>
          </div>
          <div className="row">
            <div className="col-sm-12">
              <label>Specification</label>
              <div className="help-block">Configure one or more processing calculations here.</div>
              { _spec_editor }
            </div>
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
