var React = require('react');

var util = require('utils/util');

var AppConstants = require('constants/AppConstants');
var SimpleAdmin = require('components/SimpleAdmin');
var LoadStatus = require('components/LoadStatus');
var GroupActions = require('actions/GroupActions');
var GroupStore = require('stores/GroupStore');
var RuleActions = require('actions/RuleActions');
var RuleStore = require('stores/RuleStore');
var TargetActions = require('actions/TargetActions');
var TargetStore = require('stores/TargetStore');
var SensorTypeActions = require('actions/SensorTypeActions');
var SensorTypeStore = require('stores/SensorTypeStore');
var SensorActions = require('actions/SensorActions');
var SensorStore = require('stores/SensorStore');
var mui = require('material-ui'),
  FlatButton = mui.FlatButton,
  FontIcon = mui.FontIcon;

import connectToStores from 'alt/utils/connectToStores';

@connectToStores
export default class Manage extends React.Component {
    static defaultProps = {};
    constructor(props) {
        super(props);
        this.state = {
            tab: "sensors"
        };
    }

    static getStores() {
        return [GroupStore, SensorStore, SensorTypeStore, TargetStore, RuleStore];
    }

    static getPropsFromStores() {
        var st = GroupStore.getState();
        st.sensor_types = SensorTypeStore.getState().sensor_types;
        st.sensors = SensorStore.getState().sensors;
        st.targets = TargetStore.getState().targets;
        st.rules = RuleStore.getState().rules;
        return st;
    }

    componentDidMount() {
        GroupActions.fetchGroups();
        SensorTypeActions.fetchTypes();
        TargetActions.fetchTargets();
        RuleActions.fetchRules();
    }

    gotoTab(tab) {
        this.setState({tab: tab});
    }

    render() {
        var that = this;
        var props;
        var tab = this.state.tab;
        var tabs = [
            {id: 'sensors', label: "Sensors"},
            {id: 'stypes', label: "Sensor Types"},
            {id: 'targets', label: "Targets"}
        ];
        if (tab == "sensors") {
            var group_opts = util.flattenDict(this.props.groups).map(function(group, i, arr) {
                return { val: group.id, lab: group.name };
            });
            var type_opts = util.flattenDict(this.props.sensor_types).map(function(st, i, arr) {
                return { val: st.id, lab: st.name };
            });
            var target_opts = util.flattenDict(this.props.targets).map(function(target, i, arr) {
                return { val: target.id, lab: target.name };
            });
            props = {
                'url': "/api/sensor",
                'id': 'sa',
                'entity_name': "Sensors",
                'attributes': [
                    { name: 'kn', label: "Key Name", editable: true, fixed: true },
                    { name: 'name', label: "Name", editable: true },
                    { name: 'contacts', label: "Contacts", editable: true, inputType: 'textarea', editOnly: true, hint: "JSON object with keys as user alias and values as user ID" },
                    { name: 'sensortype_id', label: "Type", editable: true, inputType: "select", opts: type_opts,
                        fromValue: function(type_id) { return (that.props.sensor_types[type_id] != null) ? that.props.sensor_types[type_id].name : "-"; } },
                    { name: 'group_ids', label: "Groups", editable: true, editOnly: true, inputType: "select", multiple: true, opts: group_opts },
                    { name: 'target_id', label: "Target", editable: true, editOnly: false, inputType: "select", opts: target_opts, fromValue: function(target_id) { return (that.props.targets[target_id] != null) ? that.props.targets[target_id].name : "-"; } }
                ],
                'add_params': {},
                'unique_key': 'key',
                'max': 50,
                getListFromJSON: function(data) { return data.data.sensors; },
                getObjectFromJSON: function(data) { return data.data.sensor; }
            }
        } else if (tab == "stypes") {

            props = {
                'url': "/api/sensortype",
                'id': 'sa',
                'entity_name': "Sensor Types",
                'attributes': [
                    { name: 'id', label: "ID" },
                    { name: 'name', label: "Name", editable: true },
                    { name: 'alias', label: "Alias", editable: true },
                    { name: 'schema', label: "Schema", editable: true,
                        hint: "JSON object, e.g. {\"length\": {\"unit\": \"m\", \"type\": \"number\"}}",
                        editOnly: true, inputType: "textarea" }
                ],
                'add_params': {},
                'unique_key': 'key',
                'max': 50,
                getListFromJSON: function(data) { return data.data.sensortypes; },
                getObjectFromJSON: function(data) { return data.data.sensortype; },
                onItemCreated: function(item) { SensorTypeActions.manualUpdate(item); }
            }

        } else if (tab == "targets") {
            var group_opts = util.flattenDict(this.props.groups).map(function(group, i, arr) {
                return { val: group.id, lab: group.name };
            });
            props = {
                'url': "/api/target",
                'id': 'sa',
                'entity_name': "Target",
                'attributes': [
                    { name: 'id', label: "ID" },
                    { name: 'name', label: "Name", editable: true },
                    { name: 'lat', label: "Latitude", editable: true },
                    { name: 'lon', label: "Longitude", editable: true },
                    { name: 'group_ids', label: "Groups", editable: true, editOnly: true, inputType: "select", multiple: true, opts: group_opts }
                ],
                'add_params': {},
                'unique_key': 'key',
                'max': 50,
                getListFromJSON: function(data) { return data.data.targets; },
                getObjectFromJSON: function(data) { return data.data.target; },
                onItemCreated: function(item) { TargetActions.manualUpdate(item); }
            }

        }
        var _tabs = tabs.map(function(t, i, arr) {
            var here = this.state.tab == t.id;
            var cn = here ? "active" : "";
            return <li role="presentation" data-t={t.id} className={cn} key={"tab"+i}><a href="javascript:void(0)" onClick={this.gotoTab.bind(this, t.id)}>{t.label}</a></li>
        }, this);
        return (
            <div>

                <h2><FontIcon className="material-icons">settings_applications</FontIcon> Manage</h2>

                <ul className="nav nav-pills">
                    { _tabs }
                </ul>

                <SimpleAdmin {...props} />

            </div>
        );
    }
};

module.exports = Manage;