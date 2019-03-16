"use strict";
var should = require('should')
, fs = require('fs')
, sandbox = require('sandboxed-module');

describe('BaseRollingFileStream', function() {
  describe('when no filename is passed', function() {
    it('should throw an error', function() {
      var BaseRollingFileStream = require('../lib/BaseRollingFileStream');
      (function() {
        new BaseRollingFileStream();
      }).should.throw();
    });
  });

  describe('default behaviour', function() {
    var stream;

    before(function() {
      var BaseRollingFileStream = require('../lib/BaseRollingFileStream');
      stream = new BaseRollingFileStream('basetest.log');
    });

    after(function(done) {
      fs.unlink('basetest.log', done);
    });

    it('should not want to roll', function() {
      stream.shouldRoll().should.eql(false);
    });

    it('should not roll', function() {
      var cbCalled = false;
      //just calls the callback straight away, no async calls
      stream.roll('basetest.log', function() { cbCalled = true; });
      cbCalled.should.eql(true);
    });

    it('should pass options to the underlying write stream', function() {
      var underlyingStreamOptions;

        var BaseRollingFileStream = sandbox.require(
          '../lib/BaseRollingFileStream',
          {
            requires: {
              'fs': {
                createWriteStream: function(filename, options) {
                  underlyingStreamOptions = options;
                  return {
                    on: function() {}
                  };
                }
              }
            },
            singleOnly: true
          }
        );
        var stream = new BaseRollingFileStream('cheese.log', { encoding: 'utf904'});
        stream.openTheStream();

        underlyingStreamOptions.should.eql({ encoding: 'utf904', mode: 420, flags: 'a'});
    });
  });

  describe('when end is called', function() {
    it('should close the underlying stream', function(done) {
      var stream = new (require('../lib/BaseRollingFileStream'))('cheese.log');
      stream.theStream.on('close', function() {
        done();
      });

      stream.end();
    });
  });

  describe('when the file is in a non-existent directory', function() {
    var stream;
    before(function() {
      var BaseRollingFileStream = require('../lib/BaseRollingFileStream');
      stream = new BaseRollingFileStream('subdir/test.log');
    });

    after(function() {
      fs.unlinkSync('subdir/test.log');
      fs.rmdir('subdir');
    });

    it('should create the directory', function() {
      fs.existsSync('subdir/test.log').should.eql(true);
      stream.end();
    });
  });
});
