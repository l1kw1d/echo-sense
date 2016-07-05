var alt = require('config/alt');
var TargetActions = require('actions/TargetActions');
import {findItemById, findIndexById} from 'utils/store-utils';
import router from 'config/router';
var toastr = require('toastr');
var util = require('utils/util');

class TargetStore {
    constructor() {
        this.bindActions(TargetActions);
        this.targets = {};
    }

    onFetchTargets(res) {
        if (res.data && res.data.targets != null) {
            this.targets = util.lookupDict(res.data.targets, 'id');
        }
    }

    onDelete(res) {
        if (res.success) {
            var id = res.data.id;
            if (id) delete this.targets[id];
        }
    }

	// Automatic

    manualUpdate(tgt) {
    	this.targets[tgt.id] = tgt;
    }


}

module.exports = alt.createStore(TargetStore, 'TargetStore');