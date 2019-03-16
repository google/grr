"use strict";
var fs = require('fs')
, zlib = require('zlib')
, debug = require('debug')('streamroller:BaseRollingFileStream')
, mkdirp = require('mkdirp')
, path = require('path')
, util = require('util')
, stream = require('readable-stream');

module.exports = BaseRollingFileStream;

function BaseRollingFileStream(filename, options) {
  debug("In BaseRollingFileStream");
  this.filename = filename;
  this.options = options || {};
  this.options.encoding = this.options.encoding || 'utf8';
  this.options.mode = this.options.mode || parseInt('0644', 8);
  this.options.flags = this.options.flags || 'a';

  this.currentSize = 0;

  function currentFileSize(file) {
    var fileSize = 0;
    try {
      fileSize = fs.statSync(file).size;
    } catch (e) {
      // file does not exist
    }
    return fileSize;
  }

  function throwErrorIfArgumentsAreNotValid() {
    if (!filename) {
      throw new Error("You must specify a filename");
    }
  }

  throwErrorIfArgumentsAreNotValid();
  debug("Calling BaseRollingFileStream.super");
  BaseRollingFileStream.super_.call(this);
  this.openTheStream();
  this.currentSize = currentFileSize(this.filename);
}
util.inherits(BaseRollingFileStream, stream.Writable);

BaseRollingFileStream.prototype._writeTheChunk = function(chunk, encoding, callback) {
  debug("writing the chunk to the underlying stream");
  this.currentSize += chunk.length;
  try {
    if (!this.theStream.write(chunk,encoding)) {
      debug('waiting for drain event');
      this.theStream.once('drain',callback);
    } else {
      process.nextTick(callback);
    }
    debug("chunk written");
  } catch (err) {
    debug(err);
    if (callback) {
      callback(err);
    }
  }
};

BaseRollingFileStream.prototype._write = function(chunk, encoding, callback) {
  debug("in _write");

  if (this.shouldRoll()) {
    this.currentSize = 0;
    this.roll(this.filename, this._writeTheChunk.bind(this, chunk, encoding, callback));
  } else {
    this._writeTheChunk(chunk, encoding, callback);
  }
};

BaseRollingFileStream.prototype.openTheStream = function(cb) {
  debug("opening the underlying stream");
  var that = this;
  mkdirp.sync(path.dirname(this.filename));
  this.theStream = fs.createWriteStream(this.filename, this.options);
  this.theStream.on('error', function(err) {
    that.emit('error', err);
  });
  if (cb) {
    this.theStream.on("open", cb);
  }
};

BaseRollingFileStream.prototype.closeTheStream = function(cb) {
  debug("closing the underlying stream");
  this.theStream.end(cb);
};

BaseRollingFileStream.prototype.compress = function(filename, cb) {
    debug('Compressing ', filename, ' -> ', filename, '.gz');
    var gzip = zlib.createGzip();
    var inp = fs.createReadStream(filename);
    var out = fs.createWriteStream(filename+".gz");
    inp.pipe(gzip).pipe(out);

    out.on('finish', function(err) {
      debug('Removing original ', filename);
      fs.unlink(filename, cb);
    });
};

BaseRollingFileStream.prototype.shouldRoll = function() {
  return false; // default behaviour is never to roll
};

BaseRollingFileStream.prototype.roll = function(filename, callback) {
  callback(); // default behaviour is not to do anything
};

BaseRollingFileStream.prototype.end = function(chunk, encoding, callback) {
  var self = this;
  debug('end called - first close myself');
  stream.Writable.prototype.end.call(self, function() {
    debug('writable end callback, now close underlying stream');
    self.theStream.end(chunk, encoding, function(err) {
      debug('underlying stream closed');
      if (callback) {
        callback(err);
      }
    });
  });
};
