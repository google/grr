# [gulp](http://gulpjs.com)-closure-deps
[![Build Status](https://secure.travis-ci.org/steida/gulp-closure-deps.png?branch=master)](http://travis-ci.org/steida/gulp-closure-deps) [![Dependency Status](https://david-dm.org/steida/gulp-closure-deps.png)](https://david-dm.org/steida/gulp-closure-deps) [![devDependency Status](https://david-dm.org/steida/gulp-closure-deps/dev-status.png)](https://david-dm.org/steida/gulp-closure-deps#info=devDependencies)

> Google Closure Library depswriter.py port for gulp


## Install

```
npm install --save-dev gulp-closure-deps
```


## Example

```js
var gulp = require('gulp');
var closureDeps = require('gulp-closure-deps');

var paths = {
  scripts: [
    'bower_components/closure-library/closure/goog/**/*.js',
    'bower_components/este-library/este/**/*.js',
    'client/**/*.js',
    'server/**/*.js'
  ]
};

gulp.task('default', function() {
  gulp.src(paths.scripts)
    .pipe(closureDeps({
      fileName: 'deps.js',
      prefix: '../../../..',
      baseDir: 'public/'
    }))
    .pipe(gulp.dest('build'));
});
```

## API

### closureDeps(options)

#### options

##### fileName

Type: `String`  
Default: `deps.js`

Generated file name.

##### prefix

Type: `String`  
Default: ``

Path prefix for paths resolving, from Closure Library base.js to root.

##### baseDir

Type: `String`
Default: ``

Optional base url for you public folder

#### methods

##### changed

Type: `String`  
Returns: `Boolean`

This method can be used in watch mode. You can pass changed file path and it
returns whether deps file should be recreated.

### Error: EMFILE Issue

OSX has default limit for opened files set to 256. Fix it with ```ulimit -n 10000```

## License

MIT © [Daniel Steigerwald](https://github.com/steida)
