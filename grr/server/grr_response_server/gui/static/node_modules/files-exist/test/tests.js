var chai = require('chai'),
filesExist = require('../lib/files-exist');

describe("filesExist", function() {
  it('should return an empty array when called with an empty array', function() {
    var fileArray = [],
    resultArray = filesExist(fileArray);
    chai.expect(fileArray).to.deep.equal(resultArray);
  });

  it('should throw an exception for a missing file', function() {
    var fileArray = ['foo.bar'];
    chai.expect(filesExist.bind(filesExist, fileArray)).to.throw('A required file is missing: foo.bar');
  });

  it('should ignore file paths which start with exclamation mark. (gulp not syntax)', function() {
    var fileArray = [ '!foo.bar'];
    var resultArray = filesExist(fileArray);

    chai.expect(fileArray).to.deep.equal(resultArray);
  });

  it('should automatically return a single element array if argument for fileExists is not an array but a string value', function() {
    var fileArg = 'package.json';
    var resultArray = filesExist(fileArg);

    chai.expect(resultArray).to.deep.equal([ fileArg ]);
  });

  it('should ignore excepted files and check the others for existence and fail if one is missing', function() {
    var fileArray = [ '!foo.bar', 'bar.foo'];
    chai.expect(filesExist.bind(filesExist, fileArray)).to.throw('A required file is missing: bar.foo');
  });

  it('should work with excepted file and a existing files', function() {
    var fileArray = ['package.json', 'test/tests.js', '!lib/files-exist.js'];
    var resultArray = filesExist(fileArray);
    chai.expect(resultArray).to.deep.equal(fileArray);
  });

  it('should return an identical array for existing files', function() {
    var fileArray = ['package.json', 'test/tests.js', 'lib/files-exist.js'],
    resultArray = filesExist(fileArray);
    chai.expect(fileArray).to.deep.equal(resultArray);
  });

  it('should return an array without the missing files when throwOnMissing is false', function() {
    var fileArray = ['package.json', 'test/tests.js', 'foo.bar', 'lib/files-exist.js'],
    expectedArray = ['package.json', 'test/tests.js', 'lib/files-exist.js'],
    resultArray;
    chai.expect(filesExist.bind(filesExist, fileArray, { throwOnMissing: false })).to.not.throw(Error);
    resultArray = filesExist(fileArray, { throwOnMissing: false });
    chai.expect(expectedArray).to.deep.equal(resultArray);
    chai.expect('foo.bar' in resultArray).to.equal(false);
  });

  it('should allow changing the exception message', function() {
    var fileArray = ['foo.bar'],
    options = { exceptionMessage: 'This is an exception' };
    chai.expect(filesExist.bind(filesExist, fileArray, options)).to.throw('This is an exception: foo.bar');
    chai.expect(filesExist.bind(filesExist, fileArray, options)).to.throw(Error);
  });

  it('should allow throwing a custom exception class', function() {
    class TestError extends Error {};
    var fileArray = ['foo.bar'],
    options = { onMissing: function(file) {
      throw new TestError('Custom error for missing file: ' + file);
    }};
    chai.expect(filesExist.bind(filesExist, fileArray, options)).to.throw(TestError);
  });

  it('should resolve glob requests', function() {
    var fileArray = ['lib/*.js', 'lib/*.foo'],
    options = { checkGlobs: true, throwOnMissing: false };
    var results = filesExist(fileArray, options);
    chai.expect(results).to.deep.equal(['lib/*.js']);
  });

  it('should ignore missing globs by default', function() {
    var fileArray = ['lib/*.png'],
    resultArray = filesExist(fileArray);
    chai.expect(fileArray).to.deep.equal(resultArray);
  });

  it('should throw error when empty glob is requested to be checked', function() {
    var fileArray = ['lib/*.png'],
    options = { checkGlobs: true };
    chai.expect(filesExist.bind(filesExist, fileArray, options)).to.throw('A required file is missing: lib/*.png');
  });

});
