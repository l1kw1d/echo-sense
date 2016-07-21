var React = require('react');
var Router = require('react-router');
var util = require('utils/util');
var FetchedList = require('components/FetchedList');
var LoadStatus = require('components/LoadStatus');
var AppConstants = require('constants/AppConstants');
var GroupedSelector = require('components/shared/GroupedSelector');
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

  renderProcesser(p) {
    var _running;
    if (p.running) _running = <i className="fa fa-refresh fa-spin" style={{color: 'green'}} />
    return (
      <li className="list-group-item" key={p.key}>
        <span className="title">{ p.label }</span>
        { _running }
        <span className="sub">Last Start: <span data-ts={p.ts_last_run_start}></span></span>
        <span className="sub">Duration: <span data-ts={util.secsToDuration(p.duration)}></span></span>
      </li>
      );
  }

  render() {
    return (
        <div>
          <h2><FontIcon className="material-icons">dashboard</FontIcon> Dashboard</h2>

          <Tabs>

            <Tab label="Processing">

              <FetchedList key="pt" params={{running: 1}} url="/api/sensorprocesstask" listProp="sensorprocesstasks" renderItem={this.renderProcesser.bind(this)} autofetch={true}/>

            </Tab>

          </Tabs>

        </div>
    );
  }
}
