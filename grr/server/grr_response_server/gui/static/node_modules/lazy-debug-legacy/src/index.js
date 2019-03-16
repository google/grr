var debug = require('debug');
var getModuleDebugId = require('./functions').getModuleDebugId;
var filter;

var cache = {};

var api = module.exports = {
  configure: function(opts) {
    if ( !opts ) opts = {};
    if ( opts.filter && typeof opts.filter === 'function' ) {
      filter = opts.filter;
      cache = {};
    }
  },
  get: function( filename, submoduleName ) {
    return debug(api.getModuleDebugName(filename, submoduleName));
  },
  getModuleDebugName: function ( filename, submoduleName ) {
    var name = cache[filename];
    if ( !name ) {
      name = getModuleDebugId(filename, {platform: process.platform, filter:filter});
      cache[filename] = name;
    }
    if ( submoduleName ) {
      return name + ':' + submoduleName;
    } else {
      return name;
    }
  }
};
