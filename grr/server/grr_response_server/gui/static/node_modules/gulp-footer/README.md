The canonical location of this project is now [tracker1/gulp-footer](https://github.com/tracker1/gulp-footer).

# gulp-footer [![NPM version](https://badge.fury.io/js/gulp-footer.png)](http://badge.fury.io/js/gulp-footer) [![Build Status](https://travis-ci.org/tracker1/gulp-footer.png)](https://travis-ci.org/tracker1/gulp-footer)

gulp-footer is a Gulp extension to add a footer to file(s) in the pipeline.  [Gulp is a streaming build system](https://github.com/gulpjs/gulp) utilizing [node.js](http://nodejs.org/).

```javascript
var footer = require('gulp-footer');
```

## API

### footer(text, data)

#### text

Type: `String`  
Default: `''`  

The template text.


#### data

Type: `Object`  
Default: `{}`  

The data object used to populate the text.


## Usage

```javascript
var footer = require('gulp-footer');

gulp.src('./foo/*.js')
  .pipe(footer('Hello'))
  .pipe(gulp.dest('./dist/')

gulp.src('./foo/*.js')
  .pipe(footer('Hello <%= name %>\n', { name : 'World'} ))
  .pipe(gulp.dest('./dist/')

gulp.src('./foo/*.js')
  .pipe(footer('Hello ${name}\n', { name : 'World'} ))
  .pipe(gulp.dest('./dist/')


//
var pkg = require('./package.json');
var banner = ['/**',
  ' * <%= pkg.name %> - <%= pkg.description %>',
  ' * @version v<%= pkg.version %>',
  ' * @link <%= pkg.homepage %>',
  ' * @license <%= pkg.license %>',
  ' */',
  ''].join('\n');

//passing in the text
gulp.src('./foo/*.js')
  .pipe(footer(banner, { pkg : pkg } ))
  .pipe(gulp.dest('./dist/')

//reading from a file for the text
var bannerText = fs.readFileSync('banner.js');

/*********************************************/
//If you want the text from a file...
var fs = require('fs');
var banner = fs.readFileSync('banner.txt');
```
