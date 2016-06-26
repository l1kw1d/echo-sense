'use strict';

var React = require('react');
var Router = require('react-router');

import AltContainer from 'alt-container';
var FluxFetchedList = require('components/FluxFetchedList');
var $ = require('jquery');
var util = require('utils/util');
var api = require('utils/api');
var mui = require('material-ui'),
  FlatButton = mui.FlatButton,
  RaisedButton = mui.RaisedButton,
  List = mui.List,
  Card = mui.Card,
  CardTitle = mui.CardTitle,
  FontIcon = mui.FontIcon,
  ListItem = mui.ListItem;

var ProcessTaskStore = require('stores/ProcessTaskStore');
var ProcessTaskActions = require('actions/ProcessTaskActions');

var IconMenu = mui.IconMenu;
var MenuItem = mui.MenuItem;
var bootbox = require('bootbox');
var Link = Router.Link;
import history from 'config/history'

export default class AnalysisSettings extends React.Component {
  static defaultProps = {
    user: null
  }

  constructor(props) {
    super(props);
    this.state = {
      tasks: [],
      loading: false
    };
  }

  componentDidMount() {

  }

  componentDidUpdate(prevProps, prevState) {

  }

  goto_task(task) {
    if (task==null) history.replaceState(null, `/app/processing/settings`);
    else history.replaceState(null, `/app/processing/settings/${task.id}`);
  }

  closeDetail() {
    this.goto_task(null);
  }

  new_task_dialog() {
    bootbox.prompt({
      title: "Enter new task label",
      callback: (result) => {
        if (result === null) {
        } else {
          ProcessTaskActions.update({label: result});
        }
      }
    });
  }

  render() {
    var detail;
    var _list;
    var center = this.state.map_center;
    return (
      <div>

        { this.props.children }

        <h2>Settings - Process Tasks</h2>

        <AltContainer store={ProcessTaskStore} actions={ function(props) {
          return {
            fetchItems: function() {
              return ProcessTaskActions.fetchTasks();
            }
          }
        } } >
          <FluxFetchedList listStyle="mui" icon={<FontIcon className="material-icons">insert_chart</FontIcon>} listProp="tasks" labelProp="label" autofetch={true} onItemClick={this.goto_task.bind(this)} store={ProcessTaskStore} actions={ProcessTaskActions} />
        </AltContainer>

        <RaisedButton label="New Process Task" primary={true} onClick={this.new_task_dialog.bind(this)} />
      </div>
    );
  }
}
