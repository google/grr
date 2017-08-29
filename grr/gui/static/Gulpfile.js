'use strict';

var gulp = require('gulp');
var gulpAngularTemplateCache = require('gulp-angular-templatecache');
var gulpClosureCompiler = require('gulp-closure-compiler');
var gulpClosureDeps = require('gulp-closure-deps');
var gulpConcat = require('gulp-concat');
var gulpInsert = require('gulp-insert');
var gulpLess = require('gulp-less');
var gulpNewer = require('gulp-newer');
var gulpPlumber = require('gulp-plumber');
var gulpSass = require('gulp-sass');
var gulpSourcemaps = require('gulp-sourcemaps');


var config = {};
config.bowerDir = './bower_components';
config.distDir = 'dist';
config.tempDir = 'tmp';

var isWatching = false;

/**
 * Third-party tasks.
 */
gulp.task('compile-third-party-js', function() {
  return gulp.src([config.bowerDir + '/jquery/dist/jquery.js',
                   config.bowerDir + '/jquery-migrate/index.js',

                   config.bowerDir + '/closurelibrary/closure/goog/base.js',

                   config.bowerDir + '/bootstrap/dist/js/bootstrap.js',

                   config.bowerDir + '/angular/angular.js',
                   config.bowerDir + '/angular-animate/angular-animate.js',
                   config.bowerDir + '/angular-cookies/angular-cookies.js',
                   config.bowerDir + '/angular-resource/angular-resource.js',

                   config.bowerDir + '/bootstrap/dist/js/bootstrap.js',

                   config.bowerDir + '/angular-bootstrap/ui-bootstrap-tpls.js',
                   config.bowerDir + '/angular-ui-router/release/angular-ui-router.js',

                   config.bowerDir + '/firebase/firebase-app.js',
                   config.bowerDir + '/firebase/firebase-auth.js',
                   config.bowerDir + '/Flot/jquery.flot.js',
                   config.bowerDir + '/Flot/jquery.flot.navigate.js',
                   config.bowerDir + '/Flot/jquery.flot.pie.js',
                   config.bowerDir + '/Flot/jquery.flot.resize.js',
                   config.bowerDir + '/Flot/jquery.flot.stack.js',
                   config.bowerDir + '/Flot/jquery.flot.time.js',

                   config.bowerDir + '/jquery-ui/jquery-ui.js',
                   config.bowerDir + '/jstree/dist/jstree.js',
                   config.bowerDir + '/moment/moment.js',

                   'third-party/jquery.splitter.js'])
      .pipe(gulpNewer(config.distDir + '/third-party.bundle.js'))
      .pipe(gulpConcat('third-party.bundle.js'))
      .pipe(gulp.dest(config.distDir));
});


gulp.task('copy-jquery-ui-images', function() {
  return gulp.src([config.bowerDir + '/jquery-ui/themes/smoothness/images/*.png'])
      .pipe(gulpNewer(config.distDir + '/images'))
      .pipe(gulp.dest(config.distDir + '/images'));
});


gulp.task('copy-fontawesome-fonts', function() {
  return gulp.src([config.bowerDir + '/font-awesome/fonts/fontawesome-webfont.*'])
      .pipe(gulp.dest('fonts')); // TODO(user): should be copied to 'dist' folder.
});

gulp.task('copy-third-party-resources', ['copy-jquery-ui-images',
                                         'copy-fontawesome-fonts'], function() {
  return gulp.src([config.bowerDir + '/jstree/dist/themes/default/*.gif',
                   config.bowerDir + '/jstree/dist/themes/default/*.png',
                   config.bowerDir + '/bootstrap/fonts/glyphicons-halflings-regular.*'])
      .pipe(gulp.dest(config.distDir));
});


gulp.task('compile-third-party-bootstrap-css', function() {
  return gulp.src('less/bootstrap_grr.less')
      .pipe(gulpNewer(config.tempDir + '/grr-bootstrap.css'))
      .pipe(gulpLess({
        paths: [
          config.bowerDir + '/bootstrap/less'
        ]
      }))
      .pipe(gulpConcat('grr-bootstrap.css'))
      .pipe(gulp.dest(config.tempDir));
});


gulp.task('compile-third-party-css', ['copy-third-party-resources',
                                      'compile-third-party-bootstrap-css'], function() {
  return gulp.src([config.bowerDir + '/jstree/dist/themes/default/style.css',
                   config.bowerDir + '/bootstrap/dist/css/bootstrap.css',
                   config.bowerDir + '/angular-bootstrap/ui-bootstrap-csp.css',
                   config.bowerDir + '/font-awesome/css/font-awesome.css',
                   config.bowerDir + '/jquery-ui/themes/smoothness/jquery-ui.css',
                   config.bowerDir + '/jquery-ui/themes/smoothness/theme.css',

                   config.tempDir + '/grr-bootstrap.css',

                   'third-party/splitter.css'])
      .pipe(gulpNewer(config.distDir + '/third-party.bundle.css'))
      .pipe(gulpConcat('third-party.bundle.css'))
      .pipe(gulp.dest(config.distDir));
});


/**
 * GRR tasks.
 */
gulp.task('compile-grr-angular-template-cache', function() {
  return gulp.src('angular-components/**/*.html')
      .pipe(gulpNewer(config.tempDir + '/templates.js'))
      .pipe(gulpAngularTemplateCache({
        module: 'grrUi.templates',
        standalone: true,
        templateHeader: 'goog.provide(\'grrUi.templates.module\');' +
            'grrUi.templates.module = angular.module(\'grrUi.templates\', []);' +
            'angular.module(\'grrUi.templates\').run(["$templateCache", function($templateCache) {'
      }))
      .pipe(gulp.dest(config.tempDir));
});


gulp.task('compile-grr-closure-ui-js', ['compile-grr-angular-template-cache'], function() {
  return gulp.src(['angular-components/**/*.js',
                   '!angular-components/**/*_test.js',
                   '!angular-components/empty-templates.js',
                   '!angular-components/externs.js',
                   config.tempDir + '/templates.js'])
      .pipe(gulpNewer(config.distDir + '/grr-ui.bundle.js'))
      .pipe(gulpPlumber({
        errorHandler: function(err) {
          console.log(err);
          this.emit('end');
          if (!isWatching) {
            process.exit(1);
          }
        }
      }))
      .pipe(gulpClosureCompiler({
        compilerPath: config.bowerDir + '/closure-compiler/compiler.jar',
        fileName: 'grr-ui.bundle.js',
        compilerFlags: {
          angular_pass: true,
          compilation_level: 'WHITESPACE_ONLY',
          dependency_mode: 'STRICT',
          entry_point: 'grrUi.appController.module',
          jscomp_off: [
            'checkTypes',
            'checkVars',
            'externsValidation',
            'invalidCasts',
          ],
          jscomp_error: [
            'missingProvide',
            'const',
            'constantProperty',
            'globalThis',
            'missingProperties',
            'missingRequire',
            'nonStandardJsDocs',
            'strictModuleDepCheck',
            'undefinedNames',
            'uselessCode',
            'visibility'
          ],
          language_out: 'ECMASCRIPT5_STRICT',
          create_source_map: config.distDir + '/grr-ui.bundle.js.map',
          source_map_format: 'V3'
        }
      }))
      .pipe(gulpInsert.append('//# sourceMappingURL=grr-ui.bundle.js.map'))
      .pipe(gulp.dest(config.distDir));
});


gulp.task('compile-grr-closure-ui-deps', function() {
  return gulp.src(['angular-components/**/*.js',
                   '!angular-components/**/*_test.js'])
      .pipe(gulpNewer(config.distDir + '/grr-ui.deps.js'))
      .pipe(gulpClosureDeps({
        fileName: 'grr-ui.deps.js',
        prefix: '../static',
        baseDir: './'
      }))
     .pipe(gulp.dest(config.distDir));
});


gulp.task('compile-grr-legacy-ui-js', function() {
  return gulp.src(['javascript/**/*.js', '!javascript/**/*_test.js'])
      .pipe(gulpConcat('grr-ui-legacy.bundle.js'))
      .pipe(gulp.dest(config.distDir));
});


gulp.task('compile-grr-ui-js', ['compile-grr-closure-ui-js',
                                'compile-grr-closure-ui-deps',
                                'compile-grr-legacy-ui-js']);


gulp.task('compile-grr-ui-css', function() {
  return gulp.src(['css/base.scss'])
      .pipe(gulpNewer(config.distDir + '/grr-ui.bundle.css'))
      .pipe(gulpPlumber({
        errorHandler: function(err) {
          console.log(err);
          this.emit('end');

          if (!isWatching) {
            process.exit(1);
          }
        }
      }))
      .pipe(gulpSass({
          includePaths: [
            '../../..'
          ]
      }).on('error', gulpSass.logError))
      .pipe(gulpConcat('grr-ui.bundle.css'))
      .pipe(gulp.dest(config.distDir));
});


/**
 * Combined compile tasks.
 */
gulp.task('compile-third-party', ['compile-third-party-js',
                                  'compile-third-party-css',
                                  'compile-third-party-bootstrap-css']);
gulp.task('compile-grr-ui', ['compile-grr-ui-js',
                             'compile-grr-ui-css']);
gulp.task('compile', ['compile-third-party',
                      'compile-grr-ui']);


/**
 * "Watch" tasks useful for development.
 */

gulp.task('watch', function() {
  isWatching = true;

  gulp.watch(['javascript/**/*.js', 'angular-components/**/*.js'],
             ['compile-grr-ui-js']);
  gulp.watch(['css/**/*.css', 'css/**/*.scss', 'angular-components/**/*.scss'],
             ['compile-grr-ui-css']);
});
