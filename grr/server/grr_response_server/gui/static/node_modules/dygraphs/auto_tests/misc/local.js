'use strict';

var DygraphsLocalTester = function() {
  this.tc = null; // Selected test case
  this.name = null; 
  this.results = [];
  this.summary = { failed: 0, passed: 0 };
  this.start;

  var self = this;
  jstestdriver.attachListener({
    start : function(tc) {
      self.start_(tc);
    },
    finish : function(tc, name, result, e) {
      self.finish_(tc, name, result, e);
    }
  });
};

/**
 * Call this to replace Dygraphs.warn so it throws an error.
 *
 * In some cases we will still allow warnings to be warnings, however.
 */
DygraphsLocalTester.prototype.overrideWarn = function() {
  // save console.warn so we can catch warnings.
  var originalWarn = console.warn;
  console.warn = function(msg) {
    // This warning is pervasive enough that we'll let it slide (for now).
    if (msg == "Using default labels. Set labels explicitly via 'labels' in the options parameter") {
      originalWarn(msg);
      return;
    }
    throw 'Warnings not permitted: ' + msg;
  }
};

DygraphsLocalTester.prototype.processVariables = function() {
  var splitVariables = function() { // http://www.idealog.us/2006/06/javascript_to_p.html
    var query = window.location.search.substring(1); 
    var args = {};
    var vars = query.split('&'); 
    for (var i = 0; i < vars.length; i++) { 
      if (vars[i].length > 0) {
        var pair = vars[i].split('='); 
        args[pair[0]] = pair[1];
      }
    }
    return args;
  }

  var findTestCase = function(stringName, className) {
    if (stringName) {
      var testCases = getAllTestCases();
      for (var idx in testCases) {
        var entry = testCases[idx];
        if (entry.name == stringName) {
          var prototype = entry.testCase;
          return new entry.testCase();
        }
      }
    } else if (className) {
      eval('tc__ = new ' + className + '()');
      return tc__;
    }
    return null;
  }

  var args = splitVariables();
  this.tc = findTestCase(args.testCaseName, args.testCase);
  this.test = args.test;
  this.command = args.command;
}

DygraphsLocalTester.prototype.createAnchor = function(href, id, text) {
  var a = document.createElement('a');
  a.href = href;
  a.id = id;
  a.textContent = text;
  return a;
}

DygraphsLocalTester.prototype.createResultsDiv = function(summary, durationms) {
  var div = document.createElement('div');
  div.id='results';

  var body = document.getElementsByTagName('body')[0];
  body.insertBefore(div, body.firstChild);

  var addText = function(div, text) {
    div.appendChild(document.createTextNode(text));
  };

  var passedAnchor = this.createAnchor('#', 'passed', '' + summary.passed + ' passed');
  var failedAnchor = this.createAnchor('#', 'failed', '' + summary.failed + ' failed');
  var allAnchor = this.createAnchor('#', 'all', '(view all)');

  addText(div, 'Test results: ');
  div.appendChild(passedAnchor);
  addText(div, ', ');
  div.appendChild(failedAnchor);
  addText(div, ', ');
  div.appendChild(allAnchor);
  addText(div, ', (' + durationms + ' ms)');

  var table = document.createElement('table');
  div.appendChild(table);
  div.appendChild(document.createElement('hr'));

  var setByClassName = function(name, displayStyle) {
    var elements = table.getElementsByClassName(name);
    for (var i = 0; i < elements.length; i++) {
      elements[i].style.display = displayStyle;
    }
  }

  passedAnchor.onclick = function() {
    setByClassName('fail', 'none');
    setByClassName('pass', 'block');

    passedAnchor.setAttribute('class', 'activeAnchor');
    failedAnchor.setAttribute('class', '');
  };
  failedAnchor.onclick = function() {
    setByClassName('fail', 'block');
    setByClassName('pass', 'none');
    passedAnchor.setAttribute('class', '');
    failedAnchor.setAttribute('class', 'activeAnchor');
  };
  allAnchor.onclick = function() {
    setByClassName('fail', 'block');
    setByClassName('pass', 'block');
    passedAnchor.setAttribute('class', '');
    failedAnchor.setAttribute('class', '');
  };
  return div;
}

DygraphsLocalTester.prototype.postResults = function(summary, durationms) {
  var resultsDiv = this.createResultsDiv(summary, durationms);

  var table = resultsDiv.getElementsByTagName('table')[0];
  for (var idx = 0; idx < this.results.length; idx++) {
    var result = this.results[idx];
    var tr = document.createElement('tr');
    tr.setAttribute('class', result.result ? 'pass' : 'fail');

    var tdResult = document.createElement('td');
    tdResult.setAttribute('class', 'outcome');
    tdResult.textContent = result.result ? 'pass' : 'fail';
    tr.appendChild(tdResult);

    var tdName = document.createElement('td');
    var s = result.name.split('.');
    var url = window.location.pathname + '?testCaseName=' + s[0] + '&test=' + s[1] + '&command=runTest';
    var a = this.createAnchor(url, null, result.name);

    tdName.appendChild(a);
    tr.appendChild(tdName);

    var tdDuration = document.createElement('td');
    tdDuration.textContent = result.duration + ' ms';
    tr.appendChild(tdDuration);

    if (result.e) {
      var tdDetails = document.createElement('td');
      var a = this.createAnchor('#', null, '(stack trace)');
      a.onclick = function(e) {
        return function() {
          alert(e + '\n' + e.stack);
        };
      }(result.e);
      tdDetails.appendChild(a);
      tr.appendChild(tdDetails);
    }

    table.appendChild(tr);
  }
}

DygraphsLocalTester.prototype.listTests = function() {
  var selector = document.getElementById('selector');

  if (selector != null) { // running a test
    var createAttached = function(name, parent) {
      var elem = document.createElement(name);
      parent.appendChild(elem);
      return elem;
    }
  
    var description = createAttached('div', selector);
    var list = createAttached('ul', selector);
    var parent = list.parentElement;
    var createLink = function(parent, title, url) {
      var li = createAttached('li', parent);
      var a = createAttached('a', li);
      a.textContent = title;
      a.href = url;
      return li;
    }
    if (this.tc == null) {
      description.textContent = 'Test cases:';
      var testCases = getAllTestCases();
      createLink(list, '(run all tests)', document.URL + '?command=runAllTests');
      for (var idx in testCases) {
        var entryName = testCases[idx].name;
        createLink(list, entryName, document.URL + '?testCaseName=' + entryName);
      }
    } else {
      description.textContent = 'Tests for ' + name;
      var names = this.tc.getTestNames();
      createLink(list, 'Run All Tests', document.URL + '&command=runAllTests');
      for (var idx in names) {
        var name = names[idx];
        createLink(list, name, document.URL + '&test=' + name + '&command=runTest');
      }
    }
  }
}

DygraphsLocalTester.prototype.run = function() {
  var executed = false;
  var start = new Date(). getTime();
  if (this.tc != null) {
    if (this.command == 'runAllTests') {
      console.log('Running all tests for ' + this.tc.name);
      this.tc.runAllTests();
      executed = true;
    } else if (this.command == 'runTest') {
      console.log('Running test ' + this.tc.name + '.' + this.test);
      this.tc.runTest(this.test);
      executed = true;
    }
  } else if (this.command == 'runAllTests') {
    console.log('Running all tests for all test cases');
    var testCases = getAllTestCases();
    for (var idx in testCases) {
      var entry = testCases[idx];
      var prototype = entry.testCase;
      this.tc = new entry.testCase();
      this.tc.runAllTests();
    }
    executed = true;
  }

  var durationms = new Date().getTime() - start;

  if (executed) {
    this.postResults(this.summary, durationms);
  } else {
    this.listTests();
  }
}

DygraphsLocalTester.prototype.start_ = function(tc) {
  this.startms_ = new Date().getTime();
}

DygraphsLocalTester.prototype.finish_ = function(tc, name, result, e) {
  var endms_ = new Date().getTime();
  this.results.push({
    name : tc.name + '.' + name,
    result : result,
    duration : endms_ - this.startms_,
    e : e
  });
  this.summary.passed += result ? 1 : 0;
  this.summary.failed += result ? 0 : 1;
}
