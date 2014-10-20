var host = 'ws://' + window.location.host + '/moi-ws/';
var jobids = {};
var moi_joblist = null;
var websocket = null;

function createButton(context, func){
    var button = document.createElement("input");
    button.type = "button";
    button.value = "Remove";
    button.onclick = function () { func(context.getAttribute("id")) };
    context.appendChild(button);
};


function setResult(job_info) {
    var results = document.createElement("a");
    results.href = job_info.handler + '/' + job_info.id;
    results.innerHTML = job_info.status;
    var state_node = document.getElementById(job_info.id + ":status");
    var para_node = state_node.parentNode;
    var remove_node = para_node.lastChild;
    para_node.insertBefore(results, remove_node);
    para_node.removeChild(state_node); 
};


function addJob(job) {
    name = job.name;
    id = job.id;
    status = job.status

    if(!(id in jobids)) {
        var para = document.createElement("p");
        para.setAttribute("id", id);
        var para_node = document.createTextNode(name + ': ');
        
        var state = document.createElement("span");
        state.setAttribute("id", id + ":status");
        var state_node = document.createTextNode(status);

        para.appendChild(para_node);
        state.appendChild(state_node);
        para.appendChild(state);
        createButton(para, function (id_to_drop) {  
                                          websocket.send(JSON.stringify({"remove": [id_to_drop]})); 
                                          removeJob(id_to_drop);
                                      }); 

        moi_joblist.appendChild(para);
        
        if((status == 'Success' || status == 'Failed') && job.handler) { 
            setResult(job);
        }
        
        jobids[id] = para;
    }
};

function removeJob(id) {
    if(id in jobids) {
        para_node = jobids[id]; //moi_joblist.getElementById(id).parentNode;
        moi_joblist.removeChild(para_node);
        delete jobids[id];
    }
};

function updateJob(job_info) {
    if((job_info.status == 'Success' || job_info.status == 'Failed') && job_info.handler) { 
        setResult(job_info);
    }
    else {
        status_msg = document.getElementById(job_info.id + ":status");
        status_msg.innerHTML = job_info.status;
    }
};

function initialize_websocket() {
    if (!("WebSocket" in window)) {
        alert("Your browser does not appear to support websockets!");
        return;
    } else {
        websocket = new WebSocket(host);
    }

    websocket.onopen = function() {
        websocket.send(JSON.stringify({"get": []}));
    };

    websocket.onclose = function(evt) {
        websocket.send(JSON.stringify("closing"));
    };

    // When the web socket receives an event
    websocket.onmessage = function(evt) {
        message = JSON.parse(evt.data);

        if(message.get) {
            for(var i=0; i < message.get.length; i++) {
                addJob(message.get[i]);
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

function initialize_moi() {
    moi_joblist = document.createElement('div');
    moi_joblist.setAttribute("id", "moi-joblist");
    document.body.appendChild(moi_joblist);
};

window.onload = initialize_websocket();
