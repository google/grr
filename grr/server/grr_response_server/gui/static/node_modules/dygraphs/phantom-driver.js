// Invoke via: ./test.sh
//
// or phantomjs phantom-driver.js [testCase.test]
//
// For more on phantomjs, visit www.phantomjs.org.

var RunAllAutoTests = function(done_callback) {

var page = require('webpage').create();

// NOTE: Cannot include '#' or '?' in this URL.
var url = 'auto_tests/misc/local.html';

// NOTE: changing the line below to this:
// page.open(url, function(status)) {
// makes phantomjs hang.
page.open(url, function(status) {
  if (status !== 'success') {
    console.warn('Page status: ' + status);
    console.log(page);
    phantom.exit();
  }

  var testCase, test;
  var verbose = false;
  var optIdx = 0;
  if (phantom.args.length > 0 && phantom.args[0] === "--verbose") {
    verbose = true;
    optIdx = 1;
  }
  if (phantom.args.length == optIdx + 1) {
    var parts = phantom.args[optIdx].split('.');
    if (2 != parts.length) {
      console.warn('Usage: phantomjs phantom-driver.js [--verbose] [testCase.test]');
      phantom.exit();
    }
    testCase = parts[0];
    test = parts[1];
  }

  var loggingOn = false;

  page.onConsoleMessage = function (msg) {
    if (msg == 'Running ' + test) {
      loggingOn = true;
    } else if (msg.substr(0, 'Running'.length) == 'Running') {
      loggingOn = false;
    }
    if (verbose || loggingOn) console.log(msg);
  };

  page.onError = function (msg, trace) {
    console.log(msg);
    trace.forEach(function(item) {
        console.log('  ', item.file, ':', item.line);
    })
  };

  var results;
  
  // Run all tests.
  var start = new Date().getTime();
  results = page.evaluate(function() {
    var num_passing = 0, num_failing = 0;
    var failures = [];

    jstestdriver.attachListener({
      finish : function(tc, name, result, e) {
        console.log("Result:", tc.name, name, result, e);
        if (result) {
          // console.log(testCase + '.' + test + ' passed');
          num_passing++;
        } else {
          num_failing++;
          failures.push(tc.name + '.' + name);
        }
      }
    });
    var testCases = getAllTestCases();
    for (var idx in testCases) {
      var entry = testCases[idx];

      var prototype = entry.testCase;
      var tc = new entry.testCase();
      var result = tc.runAllTests();
    }
    return {
      num_passing : num_passing,
      num_failing : num_failing,
      failures : failures
    };
  });
  var end = new Date().getTime();
  var elapsed = (end - start) / 1000;

  console.log('Ran ' + (results.num_passing + results.num_failing) + ' tests in ' + elapsed + 's.');
  console.log(results.num_passing + ' test(s) passed');
  console.log(results.num_failing + ' test(s) failed:');
  for (var i = 0; i < results.failures.length; i++) {
    // TODO(danvk): print an auto_test/misc/local URL that runs this test.
    console.log('  ' + results.failures[i] + ' failed.');
  }

  done_callback(results.num_failing, results.num_passing);
});

};

// Load all "tests/" pages.
var LoadAllManualTests = function(totally_done_callback) {

var fs = require('fs');
var tests = fs.list('tests');
var pages = [];

function make_barrier_closure(n, fn) {
  var calls = 0;
  return function() {
    calls++;
    if (calls == n) {
      fn();
    } else {
      // console.log('' + calls + ' done, ' + (n - calls) + ' remain');
    }
  };
}

var tasks = [];
for (var i = 0; i < tests.length; i++) {
  if (tests[i].substr(-5) != '.html') continue;
  tasks.push(tests[i]);
}
tasks = [ 'independent-series.html' ];

var loaded_page = make_barrier_closure(tasks.length, function() {
  // Wait 2 secs to allow JS errors to happen after page load.
  setTimeout(function() {
    var success = 0, failures = 0;
    for (var i = 0; i < pages.length; i++) {
      if (pages[i].success && !pages[i].hasErrors) {
        success++;
      } else {
        failures++;
      }
    }
    console.log('Successfully loaded ' + success + ' / ' +
                (success + failures) + ' test pages.');
    totally_done_callback(failures, success);
  }, 2000);
});


for (var i = 0; i < tasks.length; i++) {
  var url = 'file://' + fs.absolute('tests/' + tasks[i]);
  pages.push(function(path, url) {
    var page = require('webpage').create();
    page.success = false;
    page.hasErrors = false;
    page.onError = function (msg, trace) {
      console.log(path + ': ' + msg);
      page.hasErrors = true;
      trace.forEach(function(item) {
        console.log('  ', item.file, ':', item.line);
      });
    };
    page.onLoadFinished = function(status) {
      if (status == 'success') {
        page.success = true;
      }
      if (!page.done) loaded_page();
      page.done = true;
    };
    page.open(url);
    return page;
  }(tasks[i], url));
}

};


// First run all auto_tests.
// If they all pass, load the manual tests.
RunAllAutoTests(function(num_failing, num_passing) {
  if (num_failing !== 0) {
    console.log('FAIL');
    phantom.exit();
  } else {
    console.log('PASS');
  }
  phantom.exit();

  // This is not yet reliable enough to be useful:
  /*
  LoadAllManualTests(function(failing, passing) {
    if (failing !== 0) {
      console.log('FAIL');
    } else {
      console.log('PASS');
    }
    phantom.exit();
  });
  */
});
