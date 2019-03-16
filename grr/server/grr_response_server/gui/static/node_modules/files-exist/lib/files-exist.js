'use strict';

var glob = require('glob'),
    defaults = require('defaults'),

// Helper function by Yuriy Nemtsov
// http://stackoverflow.com/a/2441972
stringToFunction = function(str) {
  var arr = str.split("."), fn, i, len = arr.length;
  if (typeof global !== 'undefined') {
    fn = global;
  } else {
    fn = window;
  }

  for (i = 0; i < len; i++) {
    fn = fn[arr[i]];
  }

  if (typeof fn !== "function") {
    throw new Error("function not found");
  }

  return fn;
},

filesExist = function(fileArray, options) {
  options = defaults(options, {
    checkGlobs: false,
    throwOnMissing: true,
    exceptionClass: 'Error',
    exceptionMessage: 'A required file is missing',
  });

  options = defaults(options, {
    onMissing: function(filename) {
      if (options.throwOnMissing) {
        throw stringToFunction(options.exceptionClass).call(this, options.exceptionMessage + ': ' + filename);
      } else {
        return false;
      }
    }
  });

  if(typeof fileArray === 'string') {
    fileArray = [ fileArray ];
  }

  return fileArray.filter(function(file) {
    if(isExceptFileSyntax(file)) {
      return true;
    }

    if (glob.hasMagic(file) && options.checkGlobs === false) {
      return true;
    }

    // TODO: Check files asynchronously
    if (glob.sync(file).length === 0) {
      return options.onMissing(file);
    } else {
      return true;
    }
  });
};

function isExceptFileSyntax(filePath) {
  return (filePath || '').indexOf('!') === 0;
}

module.exports = filesExist;