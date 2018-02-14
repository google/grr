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
config.nodeModulesDir = './node_modules';
config.distDir = 'dist';
config.tempDir = 'tmp';

var isWatching = false;

/**
 * Third-party tasks.
 */
gulp.task('compile-third-party-js', function() {
  return gulp.src([config.nodeModulesDir + '/jquery/dist/jquery.js',
                   config.nodeModulesDir + '/jquery-migrate/dist/jquery-migrate.js',

                   config.nodeModulesDir + '/google-closure-library/closure/goog/base.js',

                   config.nodeModulesDir + '/bootstrap/dist/js/bootstrap.js',

                   config.nodeModulesDir + '/angular/angular.js',
                   config.nodeModulesDir + '/angular-animate/angular-animate.js',
                   config.nodeModulesDir + '/angular-cookies/angular-cookies.js',
                   config.nodeModulesDir + '/angular-resource/angular-resource.js',

                   config.nodeModulesDir + '/angular-ui-bootstrap/dist/ui-bootstrap-tpls.js',
                   config.nodeModulesDir + '/angular-ui-router/release/angular-ui-router.js',

                   config.nodeModulesDir + '/firebase/firebase-app.js',
                   config.nodeModulesDir + '/firebase/firebase-auth.js',
                   config.nodeModulesDir + '/Flot/jquery.flot.js',
                   config.nodeModulesDir + '/Flot/jquery.flot.navigate.js',
                   config.nodeModulesDir + '/Flot/jquery.flot.pie.js',
                   config.nodeModulesDir + '/Flot/jquery.flot.resize.js',
                   config.nodeModulesDir + '/Flot/jquery.flot.stack.js',
                   config.nodeModulesDir + '/Flot/jquery.flot.time.js',

                   config.nodeModulesDir + '/jquery-ui-dist/jquery-ui.js',
                   config.nodeModulesDir + '/jstree/dist/jstree.js',
                   config.nodeModulesDir + '/moment/moment.js',

                   'third-party/jquery.splitter.js'])
      .pipe(gulpNewer(config.distDir + '/third-party.bundle.js'))
      .pipe(gulpConcat('third-party.bundle.js'))
      .pipe(gulp.dest(config.distDir));
});


gulp.task('copy-jquery-ui-images', function() {
  return gulp.src([config.nodeModulesDir + '/jquery-ui-dist/images/*.png'])
      .pipe(gulpNewer(config.distDir + '/images'))
      .pipe(gulp.dest(config.distDir + '/images'));
});


gulp.task('copy-fontawesome-fonts', function() {
  return gulp.src([config.nodeModulesDir + '/font-awesome/fonts/fontawesome-webfont.*'])
      .pipe(gulp.dest('fonts')); // TODO(user): should be copied to 'dist' folder.
});

gulp.task('copy-third-party-resources', ['copy-jquery-ui-images',
                                         'copy-fontawesome-fonts'], function() {
  return gulp.src([config.nodeModulesDir + '/jstree/dist/themes/default/*.gif',
                   config.nodeModulesDir + '/jstree/dist/themes/default/*.png',
                   config.nodeModulesDir + '/bootstrap/fonts/glyphicons-halflings-regular.*'])
      .pipe(gulp.dest(config.distDir));
});


gulp.task('compile-third-party-bootstrap-css', function() {
  return gulp.src('less/bootstrap_grr.less')
      .pipe(gulpNewer(config.tempDir + '/grr-bootstrap.css'))
      .pipe(gulpLess({
        paths: [
          config.nodeModulesDir + '/bootstrap/less'
        ]
      }))
      .pipe(gulpConcat('grr-bootstrap.css'))
      .pipe(gulp.dest(config.tempDir));
});


gulp.task('compile-third-party-css', ['copy-third-party-resources',
                                      'compile-third-party-bootstrap-css'], function() {
  return gulp.src([config.nodeModulesDir + '/jstree/dist/themes/default/style.css',
                   config.nodeModulesDir + '/bootstrap/dist/css/bootstrap.css',
                   config.nodeModulesDir + '/angular-ui-bootstrap/dist/ui-bootstrap-csp.css',
                   config.nodeModulesDir + '/font-awesome/css/font-awesome.css',
                   config.nodeModulesDir + '/jquery-ui-dist/jquery-ui.css',
                   config.nodeModulesDir + '/jquery-ui-dist/jquery-ui-theme.css',

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
        templateHeader: 'goog.provide(\'grrUi.templates.templatesModule\');' +
            'grrUi.templates.templatesModule = angular.module(\'grrUi.templates\', []);' +
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
        compilerPath: config.nodeModulesDir + '/google-closure-compiler/compiler.jar',
        fileName: 'grr-ui.bundle.js',
        compilerFlags: {
          angular_pass: true,
          compilation_level: 'WHITESPACE_ONLY',
          dependency_mode: 'STRICT',
          entry_point: 'grrUi.appController',
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
