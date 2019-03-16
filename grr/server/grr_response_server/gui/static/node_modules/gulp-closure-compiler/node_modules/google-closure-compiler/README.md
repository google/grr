# google-closure-compiler
Check, compile, optimize and compress Javascript with Closure-Compiler

This repository tracks issues related to the publication to npmjs.org and associated plugins.
Any bugs not related to the plugins themselves should be reported to the
[main repository](https://github.com/google/closure-compiler/).

## Getting Started
Closure-compiler requires java to be installed and in the path.

If you are new to [Closure-Compiler](https://developers.google.com/closure/compiler/), make
sure to read and understand the
[compilation levels](https://developers.google.com/closure/compiler/docs/compilation_levels) as
the compiler works very differently depending on the compilation level selected.

For help or questions with the compiler, the best resource is
[Stack Overflow](http://stackoverflow.com/questions/tagged/google-closure-compiler). Posts there
are monitored by multiple Closure Compiler team members.

You may also post in the
[Closure Compiler Discuss Google Group](https://groups.google.com/forum/#!forum/closure-compiler-discuss).

Please don't cross post to both Stackoverflow and Closure Compiler Discuss.

## Usage
The compiler package now includes build tool plugins for [Grunt](http://gruntjs.com/) and
[Gulp](http://gulpjs.com/).

### Installation

```
npm install --save google-closure-compiler
```

### Configuration

The compiler has a large number of flags. The best documentation for the flags can be found by
running the `--help` command of the compiler.jar found inside the
`node_modules/google-closure-compiler` folder:

```
java -jar compiler.jar --help
```

### Specifying Options

Both the grunt and gulp tasks take options objects. The option parameters map directly to the
compiler flags without the leading '--' characters.

Values are either strings or booleans. Options which have multiple values can be arrays.

```js
  {
    js: ['/file-one.js', '/file-two.js'],
    compilation_level: 'ADVANCED',
    js_output_file: 'out.js',
    debug: true
  }
```

For advanced usages, the options may be specified as an array of strings. These values _include_
the "--" characters and are directly passed to the compiler in the order specified:

```js
  [
    '--js', '/file-one.js',
    '--js', '/file-two.js',
    '--compilation_level', 'ADVANCED',
    '--js_output_file', 'out.js',
    '--debug'
  ]
```

When an array of flags is passed, the input files should not be specified via the build tools, but
rather as compilation flags directly.

### Using the Grunt Task

Include the plugin in your Gruntfile.js:

```js
require('google-closure-compiler').grunt(grunt);
// The load-grunt-tasks plugin won't automatically load closure-compiler
```

Task targets, files and options may be specified according to the grunt
[Configuring tasks](http://gruntjs.com/configuring-tasks) guide.

#### Basic Configuration Example:

```js
require('google-closure-compiler').grunt(grunt);

// Project configuration.
grunt.initConfig({
  'closure-compiler': {
    my_target: {
      files: {
        'dest/output.min.js': ['src/js/**/*.js']
      },
      options: {
        compilation_level: 'SIMPLE',
        language_in: 'ECMASCRIPT5_STRICT',
        create_source_map: 'dest/output.min.js.map',
        output_wrapper: '(function(){\n%output%\n}).call(this)\n//# sourceMappingURL=output.min.js.map'
      }
    }
  }
});
```

#### Closure Library Example:

```js

var compilerPackage = require('google-closure-compiler');
compilerPackage.grunt(grunt);

// Project configuration.
grunt.initConfig({
  'closure-compiler': {
    my_target: {
      files: {
        'dest/output.min.js': ['src/js/**/*.js']
      },
      options: {
        js: '/node_modules/google-closure-library/**.js'
        externs: compilerPackage.compiler.CONTRIB_PATH + '/externs/jquery-1.9.js',
        compilation_level: 'SIMPLE',
        manage_closure_dependencies: true,
        language_in: 'ECMASCRIPT5_STRICT',
        create_source_map: 'dest/output.min.js.map',
        output_wrapper: '(function(){\n%output%\n}).call(this)\n//# sourceMappingURL=output.min.js.map'
      }
    }
  }
});
```

#### Advanced Usage with Arguments Array:

```js
// Project configuration.
grunt.initConfig({
  'closure-compiler': {
    my_target: {
      options: {
        // When args is present, all other options are ignored
        args: [
          '--js', '/file-one.js',
          '--js', '/file-two.js',
          '--compilation_level', 'ADVANCED',
          '--js_output_file', 'out.js',
          '--debug'
        ]
      }
    }
  }
});
```

### Using the Gulp Plugin

The gulp plugin supports piping multiple files through the compiler.

Options are a direct match to the compiler flags without the leading "--".

#### Basic Configuration Example:

```js
var closureCompiler = require('google-closure-compiler').gulp();

gulp.task('js-compile', function () {
  return gulp.src('./src/js/**/*.js', {base: './'})
      .pipe(closureCompiler({
          compilation_level: 'SIMPLE',
          warning_level: 'VERBOSE',
          language_in: 'ECMASCRIPT6_STRICT',
          language_out: 'ECMASCRIPT5_STRICT',
          output_wrapper: '(function(){\n%output%\n}).call(this)\n//# sourceMappingURL=output.min.js.map',
          js_output_file: 'output.min.js'
        }))
      .pipe(gulp.dest('./dist/js'));
});
```

### Use without gulp.src
Gulp files are all read into memory, transformed into a JSON stream, and piped through the
compiler. With large source sets this may require a large amount of memory.

Closure-compiler can natively expand file globs which will greatly alleviate this issue.

```js
var compilerPackage = require('google-closure-compiler');
var closureCompiler = compilerPackage.gulp();

gulp.task('js-compile', function () {
  return closureCompiler({
        js: './src/js/**.js',
        externs: compilerPackage.compiler.CONTRIB_PATH + '/externs/jquery-1.9.js',
        compilation_level: 'SIMPLE',
        warning_level: 'VERBOSE',
        language_in: 'ECMASCRIPT6_STRICT',
        language_out: 'ECMASCRIPT5_STRICT',
        output_wrapper: '(function(){\n%output%\n}).call(this)\n//# sourceMappingURL=output.min.js.map',
        js_output_file: 'output.min.js'
      })
      .pipe(gulp.dest('./dist/js'));
});
```

##### gulp.src base option
Gulp attempts to set the base of a glob from the point of the first wildcard. This isn't always
what is desired. Users can specify the { base: 'path' } option to `gulp.src` calls to override
this behavior.

#### Advanced Usage with Arguments Array:

```js
var closureCompiler = require('google-closure-compiler').gulp();

gulp.task('js-compile', function () {
  return closureCompiler([
        '--js', '/file-one.js',
        '--js', '/file-two.js',
        '--compilation_level', 'ADVANCED',
        '--js_output_file', 'out.js',
        '--debug'
      ])
      .pipe(gulp.dest('./dist/js'));
});
```

### Gulp Sourcemaps
The gulp plugin supports gulp sourcemaps.

```js
var closureCompiler = require('google-closure-compiler').gulp();
var sourcemaps = require('gulp-sourcemaps');

gulp.task('js-compile', function () {
  return gulp.src('./src/js/**/*.js', {base: './'})
      .pipe(sourcemaps.init())
      .pipe(closureCompiler({
          compilation_level: 'SIMPLE',
          warning_level: 'VERBOSE',
          language_in: 'ECMASCRIPT6_STRICT',
          language_out: 'ECMASCRIPT5_STRICT',
          output_wrapper: '(function(){\n%output%\n}).call(this)\n//# sourceMappingURL=output.min.js.map',
          js_output_file: 'output.min.js'
        }))
      .pipe(souremaps.write('/'))
      .pipe(gulp.dest('./dist/js'));
});
```

## Windows Path Length Limitations
Windows command shells have a maximum length for a command. This is surprisingly easy to hit when
you allow the build tools to expand globs for large sets of source files for the compiler.

This can be avoided by specifying the input globs as compiler arguments via the `--js` flag and
let it expand the files. You can even mix these techniques. Files specified via `js` option will
be included first.

A flagfile can also be used to workaround this issue.

### Grunt Example
```js
  'closure-compiler': {
    my_target: {
      files: {
        'dest/out.min.js': ['src/**/*.js']
      },
      options: {
        js: 'node_modules/google-closure-library/**.js'
        // other options here
      }
    }
  }
```

### Gulp Example
```js
var closureCompiler = require('google-closure-compiler').gulp();
gulp.src('src/**/*.js')
    .pipe(closureCompiler({
      js: 'node_modules/google-closure-library/**.js'
      // other options here
    })
    .pipe(gulp.dest('dist/out.min.js'));
```

## Plugin Authors and Native Node Usage
A low-level node class is included to facilitate spawning the compiler jar as a process from Node.
In addition, it exposes a static property with the path to the compiler jar file.

```js
var ClosureCompiler = require('google-closure-compiler').compiler;

console.log(ClosureCompiler.COMPILER_PATH); // absolute path the compiler jar
console.log(ClosureCompiler.CONTRIB_PATH); // absolute path the contrib folder which contains

var closureCompiler = new ClosureCompiler({
  js: 'file-one.js',
  compilation_level: 'ADVANCED'
});

var compilerProcess = closureCompiler.run(function(exitCode, stdOut, stdErr) {
  //compilation complete
});
```

## License
Copyright 2015 The Closure Compiler Authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Version History
Closure Compiler release notes can be found on the
[main repository wiki](https://github.com/google/closure-compiler/wiki/Binary-Downloads).
