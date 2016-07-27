var React = require('react');

var SimpleAdmin = require('components/SimpleAdmin');
var LoadStatus = require('components/LoadStatus');
var AppConstants = require('constants/AppConstants');
var SensorTypeActions = require('actions/SensorTypeActions');
var SensorTypeStore = require('stores/SensorTypeStore');
var util = require('utils/util');
import connectToStores from 'alt/utils/connectToStores';
var mui = require('material-ui'),
  FlatButton = mui.FlatButton,
  FontIcon = mui.FontIcon;

@connectToStores
export default class ManageUsers extends React.Component {
    static defaultProps = {}
    constructor(props) {
        super(props);
        this.state = {
            tab: "users"
        };
    }

    static getStores() {
        return [SensorTypeStore];
    }

    static getPropsFromStores() {
        return SensorTypeStore.getState();
    }

    gotoTab(tab) {
        this.setState({tab: tab});
    }

    render() {
        var that = this;
        var props;
        var tab = this.state.tab;
        var tabs = [
            {id: 'users', label: "Users"},
        ];
        if (tab == "users") {
            var level_opts = AppConstants.USER_LABELS.map(function(label, i) {
                return { lab: label, val: i + 1};
            })
            props = {
                'url': "/api/user",
                'id': 'sa',
                'entity_name': "Users",
                'attributes': [
                    { name: 'id', label: "ID" },
                    { name: 'name', label: "Name", editable: true },
                    { name: 'phone', label: "Phone", editable: true },
                    { name: 'email', label: "Email", editable: true },
                    { name: 'currency', label: "Currency (e.g. USD)", editable: true },
                    { name: 'level', label: "Level", editable: true, editOnly: true, inputType: "select", opts: level_opts },
                    { name: 'password', label: "Password", editable: true, editOnly: true },
                    { name: 'group_ids', label: "Groups", editable: true, editOnly: true,
                        formFromValue: function(value) {
                          return value.join(',');
                        }
                    },
                    { name: 'alert_channel', label: "Alert Channel", editable: true, editOnly: true, inputType: "select", defaultValue: 0, opts: [
                       { lab: "Disabled", val: 0 },
                       { lab: "Email", val: 1 },
                       { lab: "SMS", val: 2 },
                       { lab: "Push Notification (Android)", val: 3 }
                    ] },
                    { name: 'custom_attrs', label: "Custom Attributes", editable: true, editOnly: true, inputType: "textarea" }
                ],
                'add_params': {'order_by': 'dt_created'},
                'unique_key': 'id',
                'max': 50,
                getListFromJSON: function(data) { return data.data.users; },
                getObjectFromJSON: function(data) { return data.data.user; },
                detail_url: function(u) {
                    return `/app/users/${u.id}`;
                }
            }
        }

        var _tabs = tabs.map(function(t, i, arr) {
            var here = this.state.tab == t.id;
            var cn = here ? "active" : "";
            return <li role="presentation" key={i} data-t={t.id} className={cn}><a href="javascript:void(0)" onClick={this.gotoTab.bind(this, t.id)}>{t.label}</a></li>
        }, this);
        return (
            <div>

                <h1><FontIcon className="material-icons">people</FontIcon> Users</h1>

                <ul className="nav nav-pills">
                    { _tabs }
                </ul>

                <SimpleAdmin ref="sa" {...props} />

            </div>
        );
    }
}

module.exports = ManageUsers;