"use strict";
var BaseRollingFileStream = require('./BaseRollingFileStream')
, debug = require('debug')('streamroller:RollingFileStream')
, util = require('util')
, path = require('path')
, child_process = require('child_process')
, fs = require('fs');

module.exports = RollingFileStream;

function RollingFileStream (filename, size, backups, options) {
  //if you don't specify a size, this will behave like a normal file stream
  this.size = size || Number.MAX_SAFE_INTEGER;
  this.backups = backups || 1;

  function throwErrorIfArgumentsAreNotValid() {
    if (!filename || size <= 0) {
      throw new Error("You must specify a filename and file size");
    }
  }

  throwErrorIfArgumentsAreNotValid();

  RollingFileStream.super_.call(this, filename, options);
}
util.inherits(RollingFileStream, BaseRollingFileStream);

RollingFileStream.prototype.shouldRoll = function() {
  debug("should roll with current size ", this.currentSize, " and max size ", this.size);
  return this.currentSize >= this.size;
};

RollingFileStream.prototype.roll = function(filename, callback) {
  var that = this;
  var fileNameObj = path.parse(filename);
  var dir = fileNameObj.dir;
  var name = fileNameObj.name;
  var ext = fileNameObj.ext === '' ? '' : fileNameObj.ext.substring(1);
  var nameMatcher = new RegExp('^' + name);


  function justTheseFiles (item) {
    return nameMatcher.test(item);
  }

  function getExtensions(filename_) {
    return filename_.substring((name + '.').length).split('.');
  }

  function index(filename_) {
    debug('Calculating index of '+filename_);
    var exts = getExtensions(filename_);
    if (exts[exts.length - 1] === 'gz') {
      exts.pop();
    }
    if (that.options.keepFileExt) {
      return parseInt(exts[0], 10) || 0;
    } else {
      return parseInt(exts[exts.length - 1]) || 0;
    }
  }

  function byIndex(a, b) {
    if (index(a) > index(b)) {
      return 1;
    } else if (index(a) < index(b) ) {
      return -1;
    } else {
      return 0;
    }
  }

  function increaseFileIndex (fileToRename, cb) {
    var idx = index(fileToRename);
    debug('Index of ' + fileToRename + ' is ' + idx);
    if (idx < that.backups) {
      var newIdx =  (idx + 1).toString();
      var fileNameItems = [name];
      if (ext) {
        if (that.options.keepFileExt) {
          fileNameItems.push(newIdx, ext);
        } else {
          fileNameItems.push(ext, newIdx);
        }
      } else {
        fileNameItems.push(newIdx);
      }
      var destination = path.join(dir, fileNameItems.join('.'));
      if (that.options.compress && path.extname(fileToRename) === '.gz') {
          destination += '.gz';
      }
      //on windows, you can get a EEXIST error if you rename a file to an existing file
      //so, we'll try to delete the file we're renaming to first
      fs.unlink(destination, function (err) {
        //ignore err: if we could not delete, it's most likely that it doesn't exist
        debug('Renaming ' + fileToRename + ' -> ' + destination);
        fs.rename(path.join(dir, fileToRename), destination, function(err) {
          if (err) {
            cb(err);
          } else {
            if (that.options.compress && path.extname(fileToRename) !== '.gz') {
              that.compress(destination, cb);
            } else {
              cb();
            }
          }
        });
      });
    } else {
      cb();
    }
  }

  function renameTheFiles(cb) {
    //roll the backups (rename file.n to file.n+1, where n <= numBackups)
    debug("Renaming the old files");
    fs.readdir(path.dirname(filename), function (err, files) {
      if (err) {
        return cb(err);
      }
      var filesToProcess = files.filter(justTheseFiles).sort(byIndex);
      (function processOne(err) {
        var file = filesToProcess.pop();
        if (!file || err) { return cb(err); }
        increaseFileIndex(file, processOne);
      })();
    });
  }

  debug("Rolling, rolling, rolling");
  this.closeTheStream(
    renameTheFiles.bind(null,
      this.openTheStream.bind(this,
        callback)));

};
