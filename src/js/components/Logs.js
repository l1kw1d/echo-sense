var React = require('react');
var Router = require('react-router');

var FetchedList = require('components/FetchedList');
var LoadStatus = require('components/LoadStatus');
var util = require('utils/util');
var AppConstants = require('constants/AppConstants');
var GroupedSelector = require('components/shared/GroupedSelector');
var mui = require('material-ui'),
  DropDownMenu = mui.DropDownMenu,
  MenuItem = mui.MenuItem;
import api from 'utils/api';
var Link = Router.Link;

export default class Logs extends React.Component {
  static defaultProps = {}
  constructor(props) {
    super(props);
    this.state = {
      section: "sensors",
      additional_params: {}
    };
  }

  renderSensor(s) {
    return (
      <li className="list-group-item" key={s.kn}>
        <Link to={`/app/sensors/${s.kn}`} className="title">{ s.name }</Link>
        <span className="sub">Last Update: <span data-ts={s.ts_updated}></span></span>
      </li>
      );
  }

  renderProcesser(p) {
    var _running;
    if (p.running) _running = <i className="fa fa-refresh fa-spin" style={{color: 'green'}} />
    return (
      <li className="list-group-item" key={p.key}>
        <span className="title">{ p.label }</span>
        { _running }
        <span className="sub">Last Start: <span data-ts={p.ts_last_run_start}></span></span>
        <span className="sub">Last Finish: <span data-ts={p.ts_last_run}></span></span>
      </li>
      );
  }

  renderAlarm(a) {
    return (
      <li className="list-group-item" key={a.id}>
        <Link to={`/app/alarms/${a.sensor_kn}/${a.id}`} className="title">{ a.rule_name }</Link>
        <span className="sub ital">{ a.sensor_name }</span>
        <span className="sub" data-ts={a.ts_start}></span>
      </li>
      );
  }

  renderAPILog(al) {
    return (
      <li className="list-group-item" key={al.id}>
        <span className="title">{ al.path }</span>
        <span className="label label-default">{ al.method }</span>
        <span className="sub">{ al.status }</span>
        <span data-ts={al.ts}></span>
      </li>
      );
  }

  resend_payment(pmnt) {
    var params = {
      pkey: pmnt.key
    };
    api.post("/api/payment", params, (res) => {
      if (res.payment) {
        this.refs.fl_payments.update_item_by_key(res.payment, 'key');
      }
    });
  }

  renderPayment(pmnt) {
    var _action, _detail;
    var title = pmnt.amount + " " + pmnt.currency
    var status_text = util.findItemById(AppConstants.PAYMENT_STATUSES, pmnt.status, 'value').label;
    var user_text = pmnt.user ? (pmnt.user.name || pmnt.user.phone) : "--";
    var label_style = "default";
    if (status_text == "Requested") label_style = "warning";
    if (status_text == "Sent") label_style = "success";
    if (status_text == "Failed") {
      label_style = "danger";
      _detail = <span className="sub" style={{color: "red"}}>{ pmnt.last_gateway_response }</span>
    }
    if (pmnt.can_send) _action = (
      <a href="javascript:void(0)" className="right" title="Send / Retry" onClick={this.resend_payment.bind(this, pmnt)}><i className="fa fa-send" /></a>
      )
    return (
      <li className="list-group-item" key={pmnt.id}>
        <span className="title">{ title }</span>
        <span className={"label label-" + label_style} title={pmnt.last_gateway_response}>{ status_text }</span>
        { _detail }
        <span className="sub right">{ user_text }</span>
        <span data-ts={pmnt.ts_created}></span>
        { _action }
      </li>
      );
  }

  renderAnalysis(a) {
    return (
      <li className="list-group-item" key={a.kn}>
        <Link to={`/app/analysis/${a.kn}`} className="title">{ a.kn }</Link>
        <span className="sub">{ a.sensor_id }</span>
        <span className="sub">Created: <span data-ts={a.ts_created}></span></span>
        <span className="sub">Updated: <span data-ts={a.ts_updated}></span></span>
      </li>
      );
  }

  section_change(e, index, section) {
    this.setState({section: section});
  }

  select_sensor(s) {
    var p = this.state.additional_params;
    p.sensor_kn = s ? s.kn : null;
    this.setState({additional_params: p}, () => {
      this.refs.list.refresh();
    });
  }

  render() {
    var sensor_update_cutoff = util.nowTimestamp() - 1000*60*30; // last 30 mins
    var content;
    var sec = this.state.section;
    if (sec == "sensors") content = <FetchedList key="sensor" url="/api/sensor" params={{updated_since: sensor_update_cutoff}} listProp="sensors" renderItem={this.renderSensor.bind(this)} autofetch={true}/>
    else if (sec == "process_tasks") content = <FetchedList key="pt" url="/api/sensorprocesstask" listProp="sensorprocesstasks" renderItem={this.renderProcesser.bind(this)} autofetch={true}/>
    else if (sec == "alarms") {
      var params = { with_props: "sensor_name" };
      var sensor_kn = this.state.additional_params.sensor_kn;
      if (sensor_kn != null) params.sensor_kn = sensor_kn;
      content = (
      <div>

        <p className="lead">Optionally choose a sensor to filter alarms</p>

        <GroupedSelector
          onItemClick={this.select_sensor.bind(this)}
          type="sensors" sortProp="ts_updated" />

        <div hidden={sensor_kn == null}>
          <div className="alert alert-warning" style={{marginTop: "10px"}}>Selected Sensor Key: <b>{ sensor_kn }</b> <a href="javascript:void(0)" onClick={this.select_sensor.bind(this, null)}><i className="fa fa-close"/></a></div>
        </div>

        <FetchedList ref="list" key="alarm" url="/api/alarm" params={params} listProp="alarms" renderItem={this.renderAlarm.bind(this)} autofetch={true} paging_enabled={true} per_page={30} />

      </div>
    );
    } else if (sec == "apilogs") content = <FetchedList key="apilog" url="/api/apilog" ref="fl_logs" listProp="logs" renderItem={this.renderAPILog.bind(this)} autofetch={true} />
    else if (sec == "payments") content = <FetchedList key="payment" url="/api/payment" ref="fl_payments" params={{with_user: 1}} listProp="payments" renderItem={this.renderPayment.bind(this)} autofetch={true} />
    else if (sec == "analyses") content = <FetchedList key="analysis" url="/api/analysis" params={{with_props: 1}} listProp="analyses" renderItem={this.renderAnalysis.bind(this)} autofetch={true} />
    return (
        <div>
          <h2><i className="fa fa-list-ul"></i> Logs</h2>

          <p className="lead">Select below to change the log type</p>

          <DropDownMenu value={this.state.section} onChange={this.section_change.bind(this)}>
            <MenuItem value="sensors" primaryText="Sensors"/>
            <MenuItem value="process_tasks" primaryText="Process Tasks"/>
            <MenuItem value="alarms" primaryText="Alarms"/>
            <MenuItem value="apilogs" primaryText="API Logs"/>
            <MenuItem value="payments" primaryText="Payments"/>
            <MenuItem value="analyses" primaryText="Analyses"/>
          </DropDownMenu>

          <div className="vpad">
          { content }
          </div>

        </div>
    );
  }
}
