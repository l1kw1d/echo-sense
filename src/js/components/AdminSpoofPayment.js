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
import {clone} from 'lodash';
import connectToStores from 'alt/utils/connectToStores';
import {changeHandler} from 'utils/component-utils';

@connectToStores
@changeHandler
export default class AdminSpoofPayment extends React.Component {
    static defaultProps = {}
    constructor(props) {
        super(props);
        this.state = {
            params: [],
            form: {
                sensor_kn: null,
                format: "json",
                user_id: '',
                amount: 10
            }
        };
    }

    static getStores() {
        return [UserStore];
    }

    static getPropsFromStores() {
        return UserStore.getState();
    }

    componentDidMount() {

    }

    send() {
        var data = clone(this.state.form);
        data.spoof = 1;
        api.post("/api/payment", data, function(res) {
            bootbox.alert(JSON.stringify(res));
        })
    }

    render() {
        var {user_id, amount} = this.state.form;
        var ready = this.state.form.user_id.length > 5;
        return (
            <div>

                <h1><FontIcon className="material-icons">attach_money</FontIcon> Spoof Payment</h1>

                <div>

                    <div className="row">
                        <div className="col-sm-6 col-sm-offset-3">
                            <input type="text" className="form-control" placeholder="User ID" value={user_id} onChange={this.changeHandler.bind(this, 'form', 'user_id')} />
                            <input type="text" className="form-control" placeholder="Amount" value={amount} onChange={this.changeHandler.bind(this, 'form', 'amount')} />
                        </div>
                    </div>

                    <div className="text-center">
                        <p>This will not send any real payment, but will create a payment record.</p>
                        <a className="btn btn-success btn-lg" onClick={this.send.bind(this)} disabled={!ready}>Spoof</a>
                    </div>
                </div>
            </div>
        );
    }
}

