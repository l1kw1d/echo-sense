var alt = require('config/alt');
import api from 'utils/api';
import {clone} from 'lodash';
var $ = require('jquery');
import {post} from 'utils/action-utils';

class UserActions {

	constructor() {
		// Automatic action
		this.generateActions('loadLocalUser', 'manualUpdate');
	}

	// Manual actions

	logout() {
		console.log("Logout");
		try {
			var _this = this;
			var response = $.post('/api/logout', {}, function(res) {
				_this.dispatch({ success: response.success });
			}, 'json');
		} catch (err) {
			console.error(err);
			this.dispatch({ok: false, error: err.data});
		}
	}

	login(data) {
		try {
			var _this = this;
			var response = $.post('/api/login', data, function(res) {
				_this.dispatch({ok: res.success, user: res.data.user, error: res.message});
			}, 'json');
		} catch (err) {
			console.error(err);
			this.dispatch({ok: false, error: err.data});
		}
	}

	update(id, data) {
	    post(this, "/api/user", clone(data));
	}
}

module.exports = alt.createActions(UserActions);