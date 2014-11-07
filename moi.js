var moi = new function () {
    var host = 'ws://' + window.location.host + '/moi-ws/';
    var ws = null;
    var callbacks = {};
    var encode = JSON.stringify;
    var decode = JSON.parse;

    this.add_callback = function(action, func) {callbacks[action] = func};
    this.send = function(action, data) {
        to_send = {}; 
        to_send[action] = data;
        ws.send(encode(to_send))
    };
    
    this.init = function() {
        if (!("WebSocket" in window)) {
            alert("Your browser does not appear to support websockets!");
            return;
        }
        ws = new WebSocket(host);

        ws.onopen = function() {ws.send(encode({"get": []}))};
        ws.onclose = function(evt) {ws.send(encode({"close": null}))};
        ws.onerror = function(evt) {};

        ws.onmessage = function(evt) {
            message = decode(evt.data);
            for(var action in message) 
                if(action in callbacks) 
                    callbacks[action](message[action]);
        };
    };
};
