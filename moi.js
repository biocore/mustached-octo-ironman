var host = 'ws://' + window.location.host + '/consumer/';
var websocket = new WebSocket(host);
var jobids = {};

function createButton(context, func){
    var button = document.createElement("input");
    button.type = "button";
    button.value = "Remove";
    button.onclick = func;
    context.appendChild(button);
}

function addJob(job) {
    name = job.name;
    id = job.id;
    status = job.status

    if(!(id in jobids)) {
        jobids[id] = true;
        var para = document.createElement("p");
        var para_node = document.createTextNode(name + ': ');
        
        var state = document.createElement("span");
        var state_node = document.createTextNode(status);
        state.setAttribute("id", id);

        para.appendChild(para_node);
        state.appendChild(state_node);
        para.appendChild(state);
        createButton(para, function () { websocket.send(JSON.stringify({"remove": id})); 
                                          removeJob(id);
                                      }); 

        moi_joblist.appendChild(para);
    }
};

function removeJob(id) {
    if(id in jobids) {
        delete jobids[id];
        var para_node = document.getElementById(id).parentNode;
        moi_joblist.removeChild(para_node);
    }
};

function updateJob(job_info) {
    if((job_info.status == 'Success' || job_info.status == 'Failed') && job_info.handler) { 
        var results = document.createElement("a");
        results.href = job_info.handler + '/' + job_info.id;
        results.innerHTML = job_info.status;
        var state_node = document.getElementById(job_info.id);
        var para_node = state_node.parentNode;
        var remove_node = para_node.lastChild;
        para_node.insertBefore(results, remove_node);
        para_node.removeChild(state_node);
    }
    else {
        status_msg = document.getElementById(job_info.id);
        status_msg.innerHTML = job_info.status;
    }
};

function initialize_websocket() {

    websocket.onopen = function() {
        websocket.send(JSON.stringify("first-contact"));
    };

    // When the web socket receives an event
    websocket.onmessage = function(evt) {
        message = JSON.parse(evt.data);
        if(message.add) {
            for(var i=0; i < message.add.length; i++) {
                addJob(message.add[i]);
            }
        }

        if(message.remove) {
            for(var i=0; i < message.remove.length; i++) {
                removeJob(message.remove[i]);
            }
        }

        if(message.update) {
            for(var i=0; i < message.update.length; i++) {
                updateJob(message.update[i]);
            }
        }

    };
    websocket.onerror = function(evt) { };
};

window.onload = initialize_websocket();
var moi_joblist = document.createElement(div);
moi_joblist.setAttribute("id", "moi-joblist");
