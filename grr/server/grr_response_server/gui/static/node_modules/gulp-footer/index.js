/* jshint node: true */
'use strict';

var mapStream = require('map-stream');
var template = require('./template');

var footerPlugin = function(footerText, data) {
  footerText = footerText || '';
  return mapStream(function(file, cb){
    file.contents = Buffer.concat([
      file.contents,
      new Buffer(template(footerText, Object.assign({file : file}, data)))
    ]);
    cb(null, file);
  });
};

module.exports = footerPlugin;
