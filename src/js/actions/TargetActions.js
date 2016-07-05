var alt = require('config/alt');
import api from 'utils/api';
import {clone} from 'lodash';
import {get} from 'utils/action-utils';

class TargetActions {

	constructor() {
		// Automatic action
		this.generateActions('manualUpdate');
	}

	// Manual actions

	fetchTargets() {
	    get(this, "/api/target");
	}

	delete(key) {
	    api.post("/api/target/delete", {key: key}, (res) => {
	    	this.dispatch(res);
	    });
	}
}

module.exports = alt.createActions(TargetActions);