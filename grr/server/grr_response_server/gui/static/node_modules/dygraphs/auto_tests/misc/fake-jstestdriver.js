// Copyright (c)  2011 Google, Inc.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

/** 
 * @fileoverview Mocked-out jstestdriver api that lets me test locally.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
var jstestdriver = {
  jQuery : jQuery,
  listeners_ : [],
  announce_ : function(name, args) {
    for (var idx = 0; idx < jstestdriver.listeners_.length; idx++) {
      var listener = jstestdriver.listeners_[idx];
      if (listener[name]) {
        listener[name].apply(null, args);
      }
    }
  },
  attachListener: function(listener) {
    jstestdriver.listeners_.push(listener);
  }
};

if (!console) {
  var console = {
    log: function(x) {
      // ...
    }
  };
}

var jstd = {
  include : function(name) {
    this.sucker("Not including " + name);
  },
  sucker : function(text) {
    console.log(text + ", sucker!");
  }
};

var testCaseList = [];

function TestCase(name) {
  var testCase = function() { return this; };
  testCase.name = name;
  testCase.toString = function() {
    return "Fake test case " + name;
  };

  testCase.prototype.setUp = function() { };
  testCase.prototype.tearDown = function() { };
  testCase.prototype.name = name;
  /**
   * name can be a string, which is looked up in this object, or it can be a
   * function, in which case it's run.
   *
   * Examples:
   * var tc = new MyTestCase();
   * tc.runTest("testThis");
   * tc.runTest(tc.testThis);
   *
   * The duplication tc in runTest is irritating, but it plays well with
   * Chrome's console completion.
   */
  testCase.prototype.runTest = function(func) {
    var result = false;
    var ex = null;
    var name = typeof(func) == "string" ? func : "(anonymous function)";
    jstestdriver.announce_("start", [this, name]);
    try {
      result = this.runTest_(func);
    } catch (e) {
      ex = e;
    }
    jstestdriver.announce_("finish", [this, name, result, ex]);
    return result; // TODO(konigsberg): Remove this, and return value from runAllTests.
  }

  testCase.prototype.runTest_ = function(func) {
    this.setUp();

    var fn = null;
    var parameterType = typeof(func);
    if (typeof(func) == "function") {
      fn = func;
    } else if (typeof(func) == "string") {
      fn = this[func];
    } else {
      fail("can't supply " + typeof(func) + " to runTest");
    }

    fn.apply(this, []);
    this.tearDown();
    return true;
  };

  testCase.prototype.runAllTests = function() {
    var results = {};
    var names = this.getTestNames();
    for (var idx in names) {
      var name = names[idx];
      console.log("Running " + name);
      var result = this.runTest(name);
      results[name] = result;
    }
    console.log(prettyPrintEntity_(results));
    return results;
  };

  testCase.prototype.getTestNames = function() {
    // what's better than for ... in for non-array objects?
    var tests = [];
    for (var name in this) {
      if (name.indexOf('test') == 0 && typeof(this[name]) == 'function') {
        tests.push(name);
      }
    }
    return tests;
  }

  testCaseList.push({name : name, testCase : testCase});
  return testCase;
};

// Note: this creates a bunch of global variables intentionally.
function addGlobalTestSymbols() {
  globalTestDb = {};  // maps test name -> test function wrapper

  var num_tests = 0;
  for (var i = 0; i < testCaseList.length; i++) {
    var tc_class = testCaseList[i].testCase;
    for (var name in tc_class.prototype) {
      if (name.indexOf('test') == 0 && typeof(tc_class.prototype[name]) == 'function') {
        if (globalTestDb.hasOwnProperty(name)) {
          console.log('Duplicated test name: ' + name);
        } else {
          globalTestDb[name] = function(name, tc_class) {
            return function() {
              var tc = new tc_class;
              return tc.runTest(name);
            };
          }(name, tc_class);
          eval(name + " = globalTestDb['" + name + "'];");
          num_tests += 1;
        }
      }
    }
  }
  console.log('Loaded ' + num_tests + ' tests in ' +
              testCaseList.length + ' test cases');
}

function getAllTestCases() {
  return testCaseList;
}

jstestdriver.attachListener({
  finish : function(tc, name, result, e) {
    if (e) {
      console.log(e);
      if (e.stack) {
        console.log(e.stack);
      }
    }
  }
});

