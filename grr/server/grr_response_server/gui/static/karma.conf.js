/**
 * A configuration getter for the Karma test runner.
 *
 * @param {Object} config A default configuration object.
 */
module.exports = function(config) {
  config.set({
    // Available frameworks:
    // https://npmjs.org/browse/keyword/karma-adapter
    frameworks: ['jasmine'],

    // Available preprocessors:
    // https://npmjs.org/browse/keyword/karma-preprocessor
    preprocessors: {
      'static/angular-components/**/*.html': ['ng-html2js'],
    },

    // Available browser launchers:
    // https://npmjs.org/browse/keyword/karma-launcher
    browsers: ['ChromeHeadlessNoSandbox'],

    // Available reporters:
    // https://npmjs.org/browse/keyword/karma-reporter
    reporters: ['progress'],

    basePath: '../',

    files: [
      'static/dist/third-party.bundle.js',
      'static/node_modules/angular-mocks/angular-mocks.js',
      'static/angular-components/**/*.html',
      'static/dist/grr-ui.bundle.js',
      'static/dist/grr-ui-test.bundle.js',
      {
        pattern: 'static/dist/*.js.map',
        served: true,
        included: false,
      },
      {
        pattern: 'static/angular-components/**/*.js',
        served: true,
        included: false,
      },
    ],

    exclude: [],

    proxies: {
      '/static/': '/base/static/',
    },

    ngHtml2JsPreprocessor: {
      prependPrefix: '/',
    },

    customLaunchers: {
      ChromeHeadlessNoSandbox: {
        base: 'ChromeHeadless',
        flags: ['--no-sandbox'],
      },
    },

    // Possible values:
    // LOG_DISABLE || LOG_ERROR || LOG_WARN || LOG_INFO || LOG_DEBUG
    logLevel: config.LOG_INFO,

    port: 9876,
    colors: true,
    autoWatch: true,
    singleRun: false,
    concurrency: Infinity,
  });
};
