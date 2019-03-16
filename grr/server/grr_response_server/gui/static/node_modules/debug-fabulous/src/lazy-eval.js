

var slice = [].slice,
  objectAssign = require('object-assign');


function _resolveOutput(func, bindThis) {
  var wrapped = function() {
    var args;
    args = 1 <= arguments.length ? slice.call(arguments, 0) : [];

    // lazy function eval to keep output memory pressure down, if not used
    if (typeof args[0] === 'function') {
      args[0] = args[0]();
    }
    return func.apply(bindThis, args);
  };
  objectAssign(wrapped, func);

  return wrapped;
};


function wrapEval(debug) {

  var debugOrig = debug,
    noop = function(){};

  debug = function (namespace) {

    var instance = debugOrig(namespace);

    // if we're not enabled then don't attempt to log anything
    // if a debug namespace wraps its debug in a closure then it never allocates anything but the function itself
    if (!instance.enabled){
      objectAssign(noop, instance);
      instance = noop;
    }
    else {
      instance = _resolveOutput(instance);
    }
    return instance;
  }

  objectAssign(debug, debugOrig);

  return debug;
}

module.exports = wrapEval;
