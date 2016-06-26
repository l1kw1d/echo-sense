var React = require('react');

var SimpleAdmin = require('components/SimpleAdmin');
var LoadStatus = require('components/LoadStatus');
var AppConstants = require('constants/AppConstants');
var UserStore = require('stores/UserStore');
var util = require('utils/util');
var api = require('utils/api');
var Select = require('react-select');
var bootbox = require('bootbox');
var mui = require('material-ui'),
  FlatButton = mui.FlatButton,
  FontIcon = mui.FontIcon;

import connectToStores from 'alt/utils/connectToStores';
import {changeHandler} from 'utils/component-utils';

@connectToStores
@changeHandler
export default class AdminSpoof extends React.Component {
    static defaultProps = {}
    constructor(props) {
        super(props);
        this.state = {
            params: [],
            form: {
                sensor_kn: null,
                format: "json",
            },
            sensors: []
        };
    }

    static getStores() {
        return [UserStore];
    }

    static getPropsFromStores() {
        return UserStore.getState();
    }

    componentDidMount() {
        var that = this;
        api.get("/api/sensor", {}, function(res) {
            that.setState({sensors: res.data.sensors});
        });
    }

    get_post_url() {
        var eid = this.props.user.enterprise_id;
        var format = this.state.form.format;
        var sensor_kn = this.state.form.sensor_kn;
        return `/${eid}/inbox/${format}/${sensor_kn}`
    }

    get_post_body() {
        // JSON
        var json = {};
        this.state.params.map(function(p) {
            json[p.key] = p.value;
        });
        json['timestamp'] = util.nowTimestamp();
        return JSON.stringify([json]);
    }

    change_param(i, prop, e) {
        var val = e.target.value;
        var params = this.state.params;
        params[i][prop] = val;
        this.setState({params: params});
    }

    add_param() {
        var params = this.state.params;
        params.push({value: "", key: ""});
        this.setState({params: params});
    }

    send() {
        api.post(this.get_post_url(), this.get_post_body(), function(res) {
            bootbox.alert(JSON.stringify(res));
        })
    }

    render() {
        var _params = this.state.params.map(function(p, i) {
            return <li><input type="text" placeholder="Key" onChange={this.change_param.bind(this, i, 'key')} value={p.key} /> - <input type="text" placeholder="Value" onChange={this.change_param.bind(this, i, 'value')} value={p.value}/></li>
        }, this);
        var opts = this.state.sensors.map(function(s) {
            return {label: s.name, value: s.kn};
        });
        var ready = this.state.form.sensor_kn != null;
        return (
            <div>

                <h1><FontIcon className="material-icons">redo</FontIcon> Spoof Data</h1>

                <div>
                    <div className="row">
                        <div className="col-sm-6">
                            <label>API Call</label>
                            <pre><b>POST</b> { this.get_post_url() }</pre>
                        </div>
                        <div className="col-sm-6">
                            <label>Sensor</label>
                            <Select options={opts} value={this.state.form.sensor_kn} onChange={this.changeHandlerVal.bind(this, 'form', 'sensor_kn')} simpleValue/>
                        </div>
                    </div>

                    <label>JSON body</label>
                    <textarea value={this.get_post_body()} className="form-control" placeholder="JSON Body" disabled/>

                    <ul className="vpad">
                        { _params }
                    </ul>

                    <FlatButton label="Add Param" onClick={this.add_param.bind(this)} />

                    <div className="text-center">
                        <p>Careful, data sent here is interpereted and saved as real data</p>
                        <a className="btn btn-success btn-lg" onClick={this.send.bind(this)} disabled={!ready}>Send Data</a>
                    </div>
                </div>
            </div>
        );
    }
}

