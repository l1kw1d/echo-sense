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
export default class ManageRules extends React.Component {
    static defaultProps = {};
    constructor(props) {
        super(props);
        this.state = {
        };
    }

    static getStores() {
        return [RuleStore];
    }

    static getPropsFromStores() {
        return RuleStore.getState();
    }

    componentDidMount() {
        RuleActions.fetchRules();
    }

    render() {
        var that = this;
        var plimit_type_opts = [];
        AppConstants.RULE_PLIMIT_TYPES.forEach(function(op, i, arr) {
            if (!op.disabled) plimit_type_opts.push({ val: op.value, lab: op.label });
        });
        var trigger_opts = AppConstants.RULE_TRIGGERS.map(function(op, i, arr) {
            return { val: op.value, lab: op.label };
        });

        var props = {
            'url': "/api/rule",
            'id': 'sa',
            'entity_name': "Rule",
            'attributes': [
                { name: 'id', label: "ID" },
                { name: 'name', label: "Name", editable: true },
                { name: 'column', label: "Column", editable: true },
                { name: 'trigger', label: "Trigger", editable: true, inputType: "select", opts: trigger_opts },
                { name: 'duration', label: "Duration (ms)", editable: true,editOnly: true },
                { name: 'buffer', label: "Buffer (ms)", editable: true,editOnly: true },
                { name: 'plimit_type', label: "Period Limit Type", hint: "Type of Period (for period limit)", editable: true, editOnly: true, inputType: "select", opts: plimit_type_opts, defaultValue: -2 },
                { name: 'plimit', label: "Period Limit", hint: "Allowed alarms per period", editable: true, editOnly: true },
                { name: 'consecutive', label: "Consecutive", editable: true, editOnly: true, presets: [{value: -1, label: "Disabled"}] },
                { name: 'consecutive_limit', label: "Consecutive Limit (deactivate after)", editable: true, editOnly: true, presets: [{value: -1, label: "Disabled"}, {value: -2, label: "Any"}] },
                { name: 'value1', label: "Value 1", editable: true, editOnly: true },
                { name: 'value2', label: "Value 2", editable: true, editOnly: true },
                { name: 'value_complex', label: "Complex Value", editable: true, editOnly: true, inputType: 'textarea', hint: "JSON representation of complex rule values. See geojson.io for GeoJSON editor." },
                { name: 'alert_contacts', label: "Alert Contacts (list of contact aliases)", editable: true, editOnly: true, formFromValue: util.comma_join },
                { name: 'alert_message', label: "Alert Message", editable: true, editOnly: true },
                { name: 'payment_contacts', label: "Payment Contacts (list of contact aliases)", editable: true, editOnly: true, formFromValue: util.comma_join },
                { name: 'payment_amount', label: "Payment Amount (user currency)", editable: true, editOnly: true },
                { name: 'spec', label: "Processing Spec (JSON)", editable: true, editOnly: true, inputType: 'textarea', hint: "JSON object with processers array property to define optional processing when alarms are fired from rule" }
            ],
            'add_params': {},
            'unique_key': 'key',
            'max': 50,
            getListFromJSON: function(data) { return data.data.rules; },
            getObjectFromJSON: function(data) { return data.data.rule; },
            onItemCreated: function(item) { RuleActions.manualUpdate(item); }
        }
        return (
            <div>

                <h2>Rules</h2>

                <SimpleAdmin {...props} />

            </div>
        );
    }
};
