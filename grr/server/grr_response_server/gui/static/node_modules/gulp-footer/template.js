//The following content is a 1-1 copy of gulp-util@3.0.8/lib/template.js to preserve full compatibility after the removal of gulp-util.

var template = require('lodash.template');
var reEscape = require('lodash._reescape');
var reEvaluate = require('lodash._reevaluate');
var reInterpolate = require('lodash._reinterpolate');

var forcedSettings = {
  escape: reEscape,
  evaluate: reEvaluate,
  interpolate: reInterpolate
};

module.exports = function(tmpl, data) {
  var fn = template(tmpl, forcedSettings);

  var wrapped = function(o) {
    if (typeof o === 'undefined' || typeof o.file === 'undefined') {
      throw new Error('Failed to provide the current file as "file" to the template');
    }
    return fn(o);
  };

  return (data ? wrapped(data) : wrapped);
};
