# files-exist

[![Coverage Status](https://coveralls.io/repos/Kaivosukeltaja/files-exist/badge.svg?branch=master&service=github)](https://coveralls.io/github/Kaivosukeltaja/files-exist?branch=master)
[![Build Status](https://travis-ci.org/Kaivosukeltaja/files-exist.svg?branch=master)](https://travis-ci.org/Kaivosukeltaja/files-exist)

This simple tool accepts an array of filenames (or a single filename as a string) with or without globbing wildcards and returns an identical array if all the filenames point to existing files on the file system.

Basic usage:
```javascript
var filesExist = require('files-exist'),
files = filesExist(['package.json', 'node_modules/express/lib/express.js']);
```

## Usage in unit testing
You can use `files-exist`in your unit tests. Simply pass an array of files you want to exist and either check for errors or disable them and compare the array returned.
```javascript
var chai = require('chai'),
filesExist = require('files-exist');

describe('images', function() {
  it('should contain at least one .png file', function() {
    var files = 'images/*.png';

    // Method one: pass a bound call and check for thrown errors
    chai.expect(filesExist.bind(filesExist, files, { checkGlobs: true })).to.not.throw(Error);

    // Method two: suppress errors and check the returned results
    var results = filesExist(files, { checkGlobs: true, throwOnMissing: false });
    chai.expect('images/*.png' in results).to.not.equal(false);
  });
});
```

## Usage in build process
Use `files-exist` around your `gulp.src()` source files to notice when a soft dependency is broken. This can help you to spot newly added [bower](http://bower.io/) components that haven't been installed on your local machine yet.

```javascript
var jsLibs = [
    'vendor/jquery/dist/jquery.js',
    'vendor/jquery.stellar/jquery.stellar.min.js',
    'vendor/autofill-event/src/autofill-event.js',
    'vendor/js-cookie/src/js.cookie.js',
    'vendor/modernizr/modernizr.js',
    'vendor/lodash/lodash.js',
    'app/*.js',
    '!app/config.js' // Items starting with an exclamation point are ignored
];

gulp.task('build:js', function() {
  return gulp.src(filesExist(jsLibs, { exceptionMessage: 'Please run `bower install` to install missing library' }))
  .pipe(gulp.dest(outputPath + '/js'));
});
```

## Options

### checkGlobs

By default, `files-exist` doesn't check whether globs match any files. Set this to `true` to enable glob evaluation.

### onMissing

You can pass a callback function that gets called for every missing file. It will get one parameter, the name of the file or pattern that was not found. If you want to trigger an error, you may throw or return `false` from the callback.

```
options = { onMissing: function(file) {
  throw new TestError('Custom error for missing file: ' + file);
}};
```

Or alternatively:

```
options = { onMissing: function(file) {
  console.log('File not found: ' + file);
  return false;
}};
```

### throwOnMissing

Set this to `false` if you don't want `files-exist` to throw any exceptions when missing files are encountered. Note that you'll need to check the returned array yourself in this case, as it will be returned without the missing files.

### exceptionClass

Set the name of the exception class you want to use for the error message. Defaults to `Error`.

### exceptionMessage

Customize the message of the exception. The name of the first missing file encountered will be appended.

# Thanks
- [MartinKei](https://github.com/MartinKei) for string parameter and option to ignore files
