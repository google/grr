var path = require('path');

var functions = module.exports = {
  parseFilePath: function (file, platform, filter) {
    var delimiter = '/';
    if (typeof platform == 'function') {
      filter = platform;
      platform = false;
    }

    if (!platform) platform = process.platform;
    if (!platform) platform = 'browser';

    if (platform === 'win32') {
      delimiter = '\\';
    }
    if (platform === 'browser') {
      if ( file.indexOf('\\') !== -1 ) {
        delimiter = '\\';
      }
      if (file.indexOf('/') === 0) {
        file = file.substr(1,file.length);
      }
    }
    // should be posix..
    var candidates = file.split(delimiter);
    var modules = [];
    for ( var i = 0; i < candidates.length; ++i ) {
      if (candidates[i] && candidates[i].length ) {
        modules.push(candidates[i]);
      }
    }
    var last = modules.length - 1;
    if ( last > 0 ) {
      var fileName = removeFileExt(modules[last]);
      if ( fileName === 'index' ) {
        modules.pop();
      } else {
        modules[last] = fileName;
      }
    }
    if ( modules.length > 0 ) {
      if ( modules[0] === '..' ) {
        modules.shift();
      }
    }
    if ( filter && typeof filter === 'function' ) {
      return filter(modules);
    }
    return modules;
  },
  locatePackageJson: function(filePath, platform) {
    if (!platform) { platform = process.platform };
    var pathParts = functions.parseFilePath(filePath, platform);
    var filedir = path.dirname(filePath);
    var testdir = filedir;
    var counter = 1;
    var result;
    while (pathParts.length > counter ) {
      try {
        var testfile = path.join(testdir, 'package.json');
        return require.resolve(testfile);
      } catch( err ) {
        // ignore
      }
      var testdir = path.resolve(testdir, '..');
      counter++;
    }
    return false;
  },
  getModuleDebugId: function(filePath, options) {
    options = options || {};

    if (typeof options.platform == 'function') {
      options.filter = platform;
      options.platform = false;
    }

    if (!options.platform) { options.platform = process.platform };
    var packagePath = functions.locatePackageJson(filePath, options.platform);
    var relpath = (packagePath) ?
      path.relative(packagePath, filePath) : functions.findModuleRoot(filePath);
    var submodules = functions.parseFilePath(relpath, options.filter);

    if (options.prependPackageName){
      var packageName = (packagePath) ?
        require(packagePath).name : functions.getPseudoName(filePath);
      return packageName + ':' + submodules.join(':');
    }
    return submodules.join(':');
  },
  getPseudoName: function(filePath) {
    var search = 'node_modules';
    var idx = filePath.lastIndexOf(search);
    if ( idx === -1 ) return 'app';
    var moduleRoot = functions.findModuleRoot(filePath);
    if ( filePath.lastIndexOf('node_modules/') !== -1 )
      return moduleRoot.substr(0, moduleRoot.indexOf('/'));
    else
      return moduleRoot.substr(0, moduleRoot.indexOf('\\'));
  },
  findModuleRoot: function(filePath) {
    var search = 'node_modules';
    var idx = filePath.lastIndexOf(search);
    if ( idx === -1 ) return filePath.substr(1);
    return filePath.substr(idx+1+search.length);
  }
}

function removeFileExt(fileName) {
  var index = fileName.lastIndexOf('.');
  if ( index !== -1 )
    return fileName.substr(0, index);
  else
    return fileName;
}
