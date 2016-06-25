var alt = require('config/alt');
import api from 'utils/api';
import {clone} from 'lodash';
import {get} from 'utils/action-utils';

class ProcessTaskActions {

	constructor() {
		// Automatic action
		this.generateActions('manualUpdate', 'get_task', 'get_tasks');
	}

	// Manual actions

	fetchTasks() {
	    api.get("/api/processtask", {}, (res) => {
	    	this.dispatch(res);
	    });
	}


	fetchTask(id) {
	    api.get(`/api/processtask/${id}`, {}, (res) => {
	    	this.dispatch(res);
	    });
	}

	update(data) {
	    api.post("/api/processtask", data, (res) => {
	    	this.dispatch(res);
	    });
	}

	duplicate(key) {
	    api.post("/api/processtask/duplicate", {key: key}, (res) => {
	    	this.dispatch(res);
	    });
	}

	delete(key) {
	    api.post("/api/processtask/delete", {key: key}, (res) => {
	    	this.dispatch(res);
	    });
	}

}

module.exports = alt.createActions(ProcessTaskActions);