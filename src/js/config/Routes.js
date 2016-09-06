var React = require('react');

var Site = require('components/Site');
var App = require('components/App');
var Public = require('components/Public');
var Admin = require('components/Admin');
var Root = require('components/Root');

var Login = require('components/Login');
var Splash = require('components/Splash');
var Press = require('components/Press');
var Targets = require('components/Targets');
var Groups = require('components/Groups');
var Sensors = require('components/Sensors');
var Reports = require('components/Reports');
var Dashboard = require('components/Dashboard');
var SensorDetail = require('components/SensorDetail');
var AlarmDetail = require('components/AlarmDetail');
var AlarmViewer = require('components/AlarmViewer');
var SensorProcessTaskDetail = require('components/SensorProcessTaskDetail');
var RecordDetail = require('components/RecordDetail');
var AnalysisDetail = require('components/AnalysisDetail');
var Analyze = require('components/Analyze');
var AnalysisViewer = require('components/AnalysisViewer');
var AnalysisSettings = require('components/AnalysisSettings');
var ManageRules = require('components/ManageRules');
var ProcessTaskDetail = require('components/ProcessTaskDetail');
var TargetDetail = require('components/TargetDetail');
var GroupDetail = require('components/GroupDetail');
var Manage = require('components/Manage');
var DataViewer = require('components/DataViewer');
var ProfileEditor = require('components/ProfileEditor');
var Logs = require('components/Logs');

// Admin
var AdminManage = require('components/AdminManage');
var AdminSpoof = require('components/AdminSpoof');

// Account Admin
var ManageUsers = require('components/ManageUsers');
var UserDetail = require('components/UserDetail');

var NotFound = require('components/NotFound');

var Router = require('react-router');

var DefaultRoute = Router.DefaultRoute;
var Route = Router.Route;
var IndexRoute = Router.IndexRoute;

module.exports = (
  <Route component={Site} path="/">
    <IndexRoute component={Root} />
    <Route path="app" component={App}>
      <Route path="sensors" component={Sensors}>
        <Route path=":sensorKn" component={SensorDetail}>
          <Route path="processtask/:processtaskKn" component={SensorProcessTaskDetail} />
        </Route>
      </Route>
      <Route path="targets" component={Targets}>
        <Route path=":targetID" component={TargetDetail} />
      </Route>
      <Route path="groups" component={Groups}>
        <Route path=":groupID" component={GroupDetail} />
      </Route>
      <Route path="reports" component={Reports} />
      <Route path="alarms/:sensorKn/:aid" component={AlarmDetail} />
      <Route path="sensors/:sensorKn/alarms" component={AlarmViewer} />
      <Route path="processing" component={Analyze}>
        <Route path="viewer" component={AnalysisViewer} />
        <Route path="settings" component={AnalysisSettings}>
          <Route path=":processtaskID" component={ProcessTaskDetail} />
        </Route>
        <Route path="rules" component={ManageRules} />
        <IndexRoute component={AnalysisSettings} />
      </Route>
      <Route path="analysis/:analysisKn" component={AnalysisDetail} />
      <Route path="data/:sensorKn" component={DataViewer} />
      <Route path="data/:sensorKn/record/:recordKn" component={RecordDetail} />
      <Route path="manage" component={Manage}/>
      <Route path="dashboard" component={Dashboard}/>
      <Route path="profile" component={ProfileEditor}/>
      <Route path="logs" component={Logs}/>
      <Route path="admin" component={Admin}>
        <Route path="manage" component={AdminManage}/>
        <Route path="spoof" component={AdminSpoof}/>
      </Route>
      <Route path="users" component={ManageUsers} />
      <Route path="users/:userID" component={UserDetail}/>
      <IndexRoute component={Sensors} />
      <Route path="*" component={NotFound}/>
    </Route>
    <Route path="public" component={Public}>
      <Route path="splash" component={Splash}/>
      <Route path="press" component={Press}/>
      <Route path="login" component={Login}/>
      <IndexRoute component={Splash} />
    </Route>

  </Route>
);