'use strict';

const filesExist = require('files-exist');
const gulp = require('gulp');
const gulpAngularTemplateCache = require('gulp-angular-templatecache');
const gulpClosureCompiler = require('gulp-closure-compiler');
const gulpClosureDeps = require('gulp-closure-deps');
const gulpConcat = require('gulp-concat');
const gulpInsert = require('gulp-insert');
const gulpLess = require('gulp-less');
const gulpNewer = require('gulp-newer');
const gulpPlumber = require('gulp-plumber');
const gulpSass = require('gulp-sass');
const karma = require('karma');

const {series, parallel} = gulp;

/**
 * Validate paths with optional globs, by enforcing at least 1 matched file
 * per path.
 * @param {!Array<string>} globs Array of paths containing optional globs
 * @return {*} the same Array
 * @throws {!Error} if any glob matches zero files
 */
function validateGlobs(globs) {
  return filesExist(globs, {checkGlobs: true});
}

const config = {
  nodeModulesDir: './node_modules',
  distDir: 'dist',
  tempDir: 'tmp'
};
const NODE_MODULES = config.nodeModulesDir;

let isWatching = false;

/**
 * Handles errors in a sensible way during gulp watch.
 * @param {!Error} err the error
 */
function errorHandler(err) {
  console.log(err);
  this.emit('end');
  if (!isWatching) {
    process.exit(1);
  }
}

const closureCompilerPath =
    NODE_MODULES + '/google-closure-compiler-java/compiler.jar';

const closureCompilerFlags = {
  compilation_level: 'WHITESPACE_ONLY',
  dependency_mode: 'STRICT',
  jscomp_off: [
    'checkTypes',
    'checkVars',
    'externsValidation',
    'invalidCasts',
  ],
  jscomp_error: [
    'const',
    'constantProperty',
    'globalThis',
    'missingProvide',
    'missingProperties',
    'missingRequire',
    'nonStandardJsDocs',
    'strictModuleDepCheck',
    'undefinedNames',
    'uselessCode',
    'visibility',
  ],
  language_out: 'ECMASCRIPT6_STRICT',
  // See https://github.com/google/closure-compiler/issues/1138 for details.
  force_inject_library: [
    'base',
    'es6_runtime',
  ],
  source_map_format: 'V3'
};

/**
 * Compiles third-party JS.
 * @return {*} gulp stream
 */
function compileThirdPartyJs() {
  return gulp
      .src(validateGlobs([
        NODE_MODULES + '/jquery/dist/jquery.js',
        NODE_MODULES + '/jquery-migrate/dist/jquery-migrate.js',

        NODE_MODULES + '/google-closure-library/closure/goog/base.js',

        NODE_MODULES + '/angular/angular.js',
        NODE_MODULES + '/angular-animate/angular-animate.js',
        NODE_MODULES + '/angular-cookies/angular-cookies.js',
        NODE_MODULES + '/angular-resource/angular-resource.js',
        NODE_MODULES + '/angular-sanitize/angular-sanitize.js',

        NODE_MODULES + '/angular-ui-bootstrap/dist/ui-bootstrap-tpls.js',
        NODE_MODULES + '/angular-ui-router/release/angular-ui-router.js',

        NODE_MODULES + '/firebase/firebase-app.js',
        NODE_MODULES + '/firebase/firebase-auth.js',

        NODE_MODULES + '/dygraphs/dygraph-combined.js',

        NODE_MODULES + '/jstree/dist/jstree.js',
        NODE_MODULES + '/moment/moment.js',
        NODE_MODULES + '/marked/lib/marked.js',
        NODE_MODULES + '/split.js/dist/split.js',
      ]))
      .pipe(gulpNewer(config.distDir + '/third-party.bundle.js'))
      .pipe(gulpConcat('third-party.bundle.js'))
      .pipe(gulp.dest(config.distDir));
}

/**
 * Copies Font Awesome fonts.
 * @return {*} gulp stream
 */
function copyFontAwesomeFonts() {
  return gulp
      .src(validateGlobs(
          [NODE_MODULES + '/font-awesome/fonts/fontawesome-webfont.*']))
      .pipe(gulp.dest(
          'fonts'));  // TODO(user): should be copied to 'dist' folder.
}

/**
 * Copies third-party resources.
 * @return {*} gulp stream
 */
function copyThirdPartyResources() {
  return gulp
      .src(validateGlobs([
        NODE_MODULES + '/jstree/dist/themes/default/*.gif',
        NODE_MODULES + '/jstree/dist/themes/default/*.png',
        NODE_MODULES + '/bootstrap/fonts/glyphicons-halflings-regular.*',
      ]))
      .pipe(gulp.dest(config.distDir));
}

/**
 * Compiles third-party Bootstrap CSS.
 * @return {*} gulp stream
 */
function compileThirdPartyBootstrapCss() {
  return gulp.src(validateGlobs(['less/bootstrap_grr.less']))
      .pipe(gulpNewer(config.tempDir + '/grr-bootstrap.css'))
      .pipe(gulpLess({paths: [NODE_MODULES + '/bootstrap/less']}))
      .pipe(gulpConcat('grr-bootstrap.css'))
      .pipe(gulp.dest(config.tempDir));
}

/**
 * Compiles third-party CSS.
 * @return {*} gulp stream
 */
function compileThirdPartyCss() {
  return gulp
      .src(validateGlobs([
        NODE_MODULES + '/jstree/dist/themes/default/style.css',
        NODE_MODULES + '/bootstrap/dist/css/bootstrap.css',
        NODE_MODULES + '/angular-ui-bootstrap/dist/ui-bootstrap-csp.css',
        NODE_MODULES + '/font-awesome/css/font-awesome.css',

        config.tempDir + '/grr-bootstrap.css',
      ]))
      .pipe(gulpNewer(config.distDir + '/third-party.bundle.css'))
      .pipe(gulpConcat('third-party.bundle.css'))
      .pipe(gulp.dest(config.distDir));
}


/**
 * Compiles Angular template cache.
 * @return {*} gulp stream
 */
function compileGrrAngularTemplateCache() {
  return gulp.src(validateGlobs(['angular-components/**/*.html']))
      .pipe(gulpNewer(config.tempDir + '/templates.js'))
      .pipe(gulpAngularTemplateCache({
        module: 'grrUi.templates',
        standalone: true,
        templateHeader:
            'goog.module(\'grrUi.templates.templates.templatesModule\');' +
            'goog.module.declareLegacyNamespace();' +
            'exports = angular.module(\'grrUi.templates\', []);' +
            'angular.module(\'grrUi.templates\').run(["$templateCache", function($templateCache) {'
      }))
      .pipe(gulp.dest(config.tempDir));
}

/**
 * Compiles Closure UI JavaScript.
 * @return {*} gulp stream
 */
function compileGrrClosureUiJs() {
  return gulp
      .src(validateGlobs([
        'angular-components/**/*.js',
        '!angular-components/**/*_test.js',
        '!angular-components/empty-templates.js',
        '!angular-components/externs.js',
        config.tempDir + '/templates.js',
      ]))
      .pipe(gulpNewer(config.distDir + '/grr-ui.bundle.js'))
      .pipe(gulpPlumber({errorHandler}))
      .pipe(gulpClosureCompiler({
        compilerPath: closureCompilerPath,
        fileName: 'grr-ui.bundle.js',
        compilerFlags: Object.assign({}, closureCompilerFlags, {
          angular_pass: true,
          entry_point: 'grrUi.appController',
          externs: [
            'angular-components/externs.js',
          ],
          create_source_map: config.distDir + '/grr-ui.bundle.js.map',
          source_map_location_mapping:
              'angular-components/|/static/angular-components/',
        }),
      }))
      .pipe(gulpInsert.append('//# sourceMappingURL=grr-ui.bundle.js.map'))
      .pipe(gulp.dest(config.distDir));
}

/**
 * Compiles UI tests.
 * @return {*} gulp stream
 */
function compileGrrUiTests() {
  return gulp.src(validateGlobs(['angular-components/**/*_test.js']))
      .pipe(gulpNewer(config.distDir + '/grr-ui-test.bundle.js'))
      .pipe(gulpPlumber({errorHandler}))
      .pipe(gulpClosureCompiler({
        compilerPath: closureCompilerPath,
        fileName: 'grr-ui-test.bundle.js',
        compilerFlags: Object.assign({}, closureCompilerFlags, {
          angular_pass: true,
          compilation_level: 'BUNDLE',
          create_source_map: config.distDir + '/grr-ui-test.bundle.js.map',
          dependency_mode: 'NONE',
          externs: [
            'angular-components/externs.js',
          ],
          source_map_location_mapping:
              'angular-components/|/static/angular-components/',
        }),
      }))
      .pipe(gulpInsert.append('//# sourceMappingURL=grr-ui-test.bundle.js.map'))
      .pipe(gulp.dest(config.distDir));
}

/**
 * Compile Closure UI dependencies.
 * @return {*} gulp stream
 */
function compileGrrClosureUiDeps() {
  return gulp
      .src(validateGlobs(
          ['angular-components/**/*.js', '!angular-components/**/*_test.js']))
      .pipe(gulpNewer(config.distDir + '/grr-ui.deps.js'))
      .pipe(gulpClosureDeps(
          {fileName: 'grr-ui.deps.js', prefix: '../static', baseDir: './'}))
      .pipe(gulp.dest(config.distDir));
}

/**
 * Compiles CSS.
 * @return {*} gulp stream
 */
function compileGrrUiCss() {
  return gulp.src(validateGlobs(['css/base.scss']))
      .pipe(gulpNewer(config.distDir + '/grr-ui.bundle.css'))
      .pipe(gulpPlumber({errorHandler}))
      .pipe(gulpSass({
              includePaths: ['../../../../../']
            }).on('error', gulpSass.logError))
      .pipe(gulpConcat('grr-ui.bundle.css'))
      .pipe(gulp.dest(config.distDir));
}

/**
 * Starts a Karma server for testing.
 * @param {function()} done called, when testing is done.
 */
function startKarmaServer(done) {
  let config = {
    configFile: __dirname + '/karma.conf.js',
    browsers: ['ChromeHeadlessNoSandbox'],
    singleRun: true,
  };

  new karma.Server(config, done).start();
}

const compileGrrUiJs = parallel(
    series(compileGrrAngularTemplateCache, compileGrrClosureUiJs),
    compileGrrClosureUiDeps,
);

const compile = parallel(
    compileGrrUiJs,
    compileGrrUiCss,
    compileGrrUiTests,
    compileThirdPartyJs,
    series(
        parallel(
            series(copyFontAwesomeFonts, copyThirdPartyResources),
            compileThirdPartyBootstrapCss),
        compileThirdPartyCss),
);

/**
 * Watches files and triggers recompilation. Useful for development.
 */
function watch() {
  isWatching = true;

  gulp.watch(['angular-components/**/*.js'], compileGrrUiJs);
  gulp.watch(['css/*', 'angular-components/**/*.scss'], compileGrrUiCss);
}

exports.watch = watch;
exports.compile = compile;
exports.test = series(compile, startKarmaServer);
