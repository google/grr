# karma-spec-reporter

[![Join the chat at https://gitter.im/mlex/karma-spec-reporter](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/mlex/karma-spec-reporter?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge) [![Build Status](https://travis-ci.org/mlex/karma-spec-reporter.svg)](https://travis-ci.org/mlex/karma-spec-reporter)
[![Coverage Status](https://coveralls.io/repos/mlex/karma-spec-reporter/badge.svg?branch=master&service=github)](https://coveralls.io/github/mlex/karma-spec-reporter?branch=master)

Test reporter, that prints detailed results to console (similar to mocha's spec reporter).

## Usage

To use in your own Node.js project, just execute
```
npm install karma-spec-reporter --save-dev
```
This will download the karma-spec-reporter and add the dependency to `package.json`.

Then add ``'spec'`` to reporters in karma.conf.js, e.g.

```
reporters: ['spec']
```

Take a look at the [karma-spec-reporter-example](http://github.com/mlex/karma-spec-reporter-example) repository to see the reporter in action.

## Configuration

To limit the number of lines logged per test or suppress specific reporting, use the `specReporter` configuration in your
karma.conf.js file
``` js
//karma.conf.js
...
  config.set({
    ...
      reporters: ["spec"],
      specReporter: {
        maxLogLines: 5,             // limit number of lines logged per test
        suppressErrorSummary: true, // do not print error summary
        suppressFailed: false,      // do not print information about failed tests
        suppressPassed: false,      // do not print information about passed tests
        suppressSkipped: true,      // do not print information about skipped tests
        showSpecTiming: false,      // print the time elapsed for each spec
        failFast: true              // test would finish with error when a first fail occurs. 
      },
      plugins: ["karma-spec-reporter"],
    ...
```

## Contributing

### Running tests

To run the tests for the index.js file, run: `npm test`

### Generating Coverage

To see the coverage report for the module, run: `npm run coverage`
