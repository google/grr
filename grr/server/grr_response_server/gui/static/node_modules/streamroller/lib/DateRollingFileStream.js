"use strict";
var BaseRollingFileStream = require('./BaseRollingFileStream')
  , debug = require('debug')('streamroller:DateRollingFileStream')
  , format = require('date-format')
  , fs = require('fs')
  , path = require('path')
  , util = require('util');

module.exports = DateRollingFileStream;

function findTimestampFromFileIfExists(filename, now) {
  return fs.existsSync(filename) ? fs.statSync(filename).mtime : new Date(now());
}

function DateRollingFileStream(filename, pattern, options, now) {
  debug("Now is ", now);
  if (pattern && typeof(pattern) === 'object') {
    now = options;
    options = pattern;
    pattern = null;
  }
  this.pattern = pattern || '.yyyy-MM-dd';
  this.now = now || Date.now;
  this.lastTimeWeWroteSomething = format.asString(
    this.pattern,
    findTimestampFromFileIfExists(filename, this.now)
  );

  this.baseFilename = filename;
  this.alwaysIncludePattern = false;

  debug('options is ', options);

  if (options) {
    if (options.alwaysIncludePattern) {
      debug('always include pattern is true');
      this.alwaysIncludePattern = true;
      filename = this.baseFilename + this.lastTimeWeWroteSomething;
      debug('filename is now ', filename);
    }
  }
  debug("this.now is ", this.now, ", now is ", now);

  DateRollingFileStream.super_.call(this, filename, options);
}
util.inherits(DateRollingFileStream, BaseRollingFileStream);

DateRollingFileStream.prototype.shouldRoll = function () {
  var lastTime = this.lastTimeWeWroteSomething,
    thisTime = format.asString(this.pattern, new Date(this.now()));

  debug("DateRollingFileStream.shouldRoll with now = ",
    this.now(), ", thisTime = ", thisTime, ", lastTime = ", lastTime);

  this.lastTimeWeWroteSomething = thisTime;
  this.previousTime = lastTime;

  return thisTime !== lastTime;
};

DateRollingFileStream.prototype.roll = function (filename, callback) {
  var that = this;

  debug("Starting roll");

  var filenameObj = path.parse(this.baseFilename);

  if (this.alwaysIncludePattern) {
    this.filename = this.options.keepFileExt ?
      path.join(
        filenameObj.dir,
        filenameObj.name + this.lastTimeWeWroteSomething + filenameObj.ext
      ) :
      this.baseFilename + this.lastTimeWeWroteSomething;
    this.closeTheStream(
      this.compressIfNeeded.bind(this, filename,
        this.removeOldFilesIfNeeded.bind(this,
          this.openTheStream.bind(this, callback))));
  } else {
    var newFilename = this.options.keepFileExt ?
      path.join(filenameObj.dir, filenameObj.name + this.previousTime + filenameObj.ext) :
      this.baseFilename + this.previousTime;
    this.closeTheStream(
      deleteAnyExistingFile.bind(null,
        renameTheCurrentFile.bind(null,
          this.compressIfNeeded.bind(this, newFilename,
            this.removeOldFilesIfNeeded.bind(this,
              this.openTheStream.bind(this, callback))))));
  }

  function deleteAnyExistingFile(cb) {
    //on windows, you can get a EEXIST error if you rename a file to an existing file
    //so, we'll try to delete the file we're renaming to first
    fs.unlink(newFilename, function (err) {

      //ignore err: if we could not delete, it's most likely that it doesn't exist
      cb();
    });
  }

  function renameTheCurrentFile(cb) {
    debug("Renaming the ", filename, " -> ", newFilename);
    fs.rename(filename, newFilename, cb);
  }
};

DateRollingFileStream.prototype.compressIfNeeded = function (filename, cb) {
  debug("Checking if we need to compress the old file");
  if (this.options.compress) {
    this.compress(filename, cb);
  } else {
    cb();
  }
};

DateRollingFileStream.prototype.removeOldFilesIfNeeded = function (cb) {
  debug("Checking if we need to delete old files");
  if (this.options.daysToKeep && this.options.daysToKeep > 0) {
    var oldestDate = new Date(this.now() - (this.options.daysToKeep * (24 * 60 * 60 * 1000)));
    debug("Will delete any log files modified before ", oldestDate.toString());

    this.removeFilesOlderThan(oldestDate);
  }
  cb();
};

DateRollingFileStream.prototype.removeFilesOlderThan = function (oldestDate) {

  // Loop through any log files and delete any whose mtime is earlier than oldestDate
  var dirToScan = path.dirname(this.baseFilename);
  var fileToMatch = path.basename(this.baseFilename);
  var filesToCheck = fs.readdirSync(dirToScan).filter(function (file) {
    return file.indexOf(fileToMatch) > -1;
  });
  for (var i = 0; i < filesToCheck.length; i++) {
    var fileToCheck = path.join(dirToScan, filesToCheck[i]);
    var fileStats = fs.statSync(fileToCheck);
    if (fileStats.mtime < oldestDate) {
      debug("Deleting old log ", filesToCheck);
      fs.unlinkSync(fileToCheck);
    }
  }
};
