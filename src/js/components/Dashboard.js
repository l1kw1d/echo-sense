var React = require('react');
var Router = require('react-router');
var util = require('utils/util');
var FetchedList = require('components/FetchedList');
var LoadStatus = require('components/LoadStatus');
var AppConstants = require('constants/AppConstants');
var GroupedSelector = require('components/shared/GroupedSelector');
var api = require('utils/api');
var mui = require('material-ui'),
  DropDownMenu = mui.DropDownMenu,
  Tabs = mui.Tabs,
  Tab = mui.Tab,
  FontIcon = mui.FontIcon,
  MenuItem = mui.MenuItem;

var Link = Router.Link;

export default class Dashboard extends React.Component {
  static defaultProps = {}
  constructor(props) {
    super(props);
    this.state = {
      section: "processing",
      additional_params: {}
    };
  }

  clean_up(p) {
    var sptkey = p.key;
    api.post("/api/sensorprocesstask/clean_up", {sptkey: sptkey}, (res) => {
      this.refs.list.remove_item_by_key(sptkey);
    });
  }

  renderProcesser(p) {
    var _running;
    if (p.running) _running = <i className="fa fa-refresh fa-spin" style={{color: 'green'}} />
    return (
      <li className="list-group-item" key={p.key}>
        <span className="title">{ p.label }</span>
        { _running }
        <span className="sub">Last Start: <span data-ts={p.ts_last_run_start}></span></span>
        <a href="javascript:void(0)" className="right" onClick={this.clean_up.bind(this, p)}><i className="fa fa-close"/> Clean Up</a>
      </li>
      );
  }

  render() {
    return (
        <div>
          <h2><FontIcon className="material-icons">dashboard</FontIcon> Dashboard</h2>

          <Tabs>

            <Tab label="Processing">

              <FetchedList ref="list" key="pt" params={{running: 1}} url="/api/sensorprocesstask" listProp="sensorprocesstasks" renderItem={this.renderProcesser.bind(this)} autofetch={true}/>

            </Tab>

          </Tabs>

        </div>
    );
  }
}
