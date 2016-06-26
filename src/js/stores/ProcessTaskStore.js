var alt = require('config/alt');
var ProcessTaskActions = require('actions/ProcessTaskActions');
import {findItemById, findIndexById} from 'utils/store-utils';
import {isEmpty} from 'lodash';
import router from 'config/router';
var toastr = require('toastr');
var util = require('utils/util');

class ProcessTaskStore {
    constructor() {
        this.bindActions(ProcessTaskActions);
        this.tasks = {}; // id -> process task
		this.exportPublicMethods({
		});
    }

    onFetchTasks(res) {
        if (res.data && res.data.processtasks != null) {
            this.tasks = util.lookupDict(res.data.processtasks, 'id');
        }
    }

    onFetchTask(res) {
        if (res.data && res.data.processtask != null) {
            var t = res.data.processtask;
            t.updated_ms = util.nowTimestamp(); // ms
            this.tasks[t.id] = t;
        }
    }

    onUpdate(res) {
        if (res.data && res.data.processtask != null) {
            var task = res.data.processtask;
            task.updated_ms = util.nowTimestamp(); // ms
            this.tasks[task.id] = task;
        }
    }

    onDuplicate(res) {
        if (res.data && res.data.processtask != null) {
            var task = res.data.processtask;
            task.updated_ms = util.nowTimestamp(); // ms
            this.tasks[task.id] = task;
        }
    }

    onDelete(res) {
        if (res.success) {
            var id = res.data.id;
            if (id) delete this.tasks[id];
        }
    }


    // Public

	// Automatic

    manualUpdate(grp) {
    	this.tasks[grp.id] = grp;
    }

    get_task(id) {
        var task = this.tasks[id];
        if (!task) ProcessTaskActions.fetchTask(id);
        return task;
    }

    get_tasks() {
        var tasks = this.tasks;
        if (isEmpty(tasks)) {
            ProcessTaskActions.fetchTasks()
            return {};
        } else {
            return tasks;
        }
    }



}

module.exports = alt.createStore(ProcessTaskStore, 'ProcessTaskStore');