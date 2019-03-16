var wrapLazyEval = require('./src/lazy-eval'),
  wrapLazy = require('./src/lazy-debug');

module.exports = function (debug) {
  debug = debug ? debug : require('debug')

  debug = wrapLazyEval(debug);
  wrapLazy(debug);

  return debug;
}
