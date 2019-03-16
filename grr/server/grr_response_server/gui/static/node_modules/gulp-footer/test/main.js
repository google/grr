/* jshint node: true */
/* global describe, it, beforeEach */
'use strict';

var footer = require('../');
var should = require('should');
var Vinyl = require('vinyl');
require('mocha');

describe('gulp-footer', function() {
  var fakeFile;

  function getFakeFile(fileContent){
    return new Vinyl({
      path: './test/fixture/file.js',
      cwd: './test/',
      base: './test/fixture/',
      contents: new Buffer(fileContent || '')
    });
  }

  beforeEach(function(){
    fakeFile = getFakeFile('Hello world');
  });

  describe('footer', function() {

    it('file should pass through', function(done) {
      var file_count = 0;
      var stream = footer();
      stream.on('data', function(newFile){
        should.exist(newFile);
        should.exist(newFile.path);
        should.exist(newFile.relative);
        should.exist(newFile.contents);
        newFile.path.should.equal('./test/fixture/file.js');
        newFile.relative.should.equal('file.js');
        newFile.contents.toString().should.equal('Hello world');
        ++file_count;
      });

      stream.once('end', function () {
        file_count.should.equal(1);
        done();
      });

      stream.write(fakeFile);
      stream.end();
    });


    it('should append the footer to the file content', function(done) {
      var stream = footer(' : before I said');
      stream.on('data', function (newFile) {
        should.exist(newFile.contents);
        newFile.contents.toString().should.equal('Hello world : before I said');
      });
      stream.once('end', done);

      stream.write(fakeFile);
      stream.end();
    });


    it('should format the footer', function(done) {
      var stream = footer(' : and then <%= foo %> said', { foo : 'you' } );
      //var stream = footer('And then ${foo} said : ', { foo : 'you' } );
      stream.on('data', function (newFile) {
        should.exist(newFile.contents);
        newFile.contents.toString().should.equal('Hello world : and then you said');
      });
      stream.once('end', done);

      stream.write(fakeFile);
      stream.end();
    });


    it('should format the footer (ES6 delimiters)', function(done) {
      var stream = footer(' : and then ${foo} said', { foo : 'you' } );
      stream.on('data', function (newFile) {
        should.exist(newFile.contents);
        newFile.contents.toString().should.equal('Hello world : and then you said');
      });
      stream.once('end', done);

      stream.write(fakeFile);
      stream.end();
    });


    it('should access to the current file', function(done) {
      var stream = footer('\n<%= file.relative %>\n<%= file.path %>');
      stream.on('data', function (newFile) {
        should.exist(newFile.contents);
        newFile.contents.toString().should.equal('Hello world\nfile.js\n./test/fixture/file.js');
      });
      stream.once('end', done);

      stream.write(fakeFile);
      stream.end();
    });

  });

});
