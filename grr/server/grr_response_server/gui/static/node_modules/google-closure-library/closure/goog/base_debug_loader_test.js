// Copyright 2006 The Closure Library Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.


/**
 * @fileoverview Unit tests for Closure's base.js that require debug loading.
 */

goog.provide('goog.baseDebugLoaderTest');

goog.setTestOnly('goog.baseDebugLoaderTest');

goog.require('goog.functions');
goog.require('goog.testing.PropertyReplacer');
goog.require('goog.testing.jsunit');
goog.require('goog.testing.recordFunction');
goog.require('goog.userAgent');

var stubs = new goog.testing.PropertyReplacer();
var originalGoogBind = goog.bind;

function tearDown() {
  goog.setCssNameMapping(undefined);
  stubs.reset();
  goog.bind = originalGoogBind;
}

function testInHtmlDocument() {
  var savedGoogGlobal = goog.global;
  try {
    goog.global = {};
    assertFalse(goog.inHtmlDocument_());
    goog.global.document = {};
    assertFalse(goog.inHtmlDocument_());
    goog.global.document.write = function() {};
    assertTrue(goog.inHtmlDocument_());
  } finally {
    // Restore context to respect other tests.
    goog.global = savedGoogGlobal;
  }
}

function testLoadInNonHtmlNotThrows() {
  var savedGoogGlobal = goog.global;
  try {
    goog.global = {};
    goog.global.document = {};
    assertFalse(goog.inHtmlDocument_());
    // The goog code which is executed at load.
    goog.findBasePath_();
    goog.writeScriptTag_(goog.basePath + 'deps.js');
  } finally {
    // Restore context to respect other tests.
    goog.global = savedGoogGlobal;
  }
}

function testLoadBaseWithQueryParamOk() {
  var savedGoogGlobal = goog.global;
  try {
    goog.global = {};
    goog.global.document = {
      write: goog.nullFunction,
      getElementsByTagName:
          goog.functions.constant([{src: '/path/to/base.js?zx=5'}])
    };
    assertTrue(goog.inHtmlDocument_());
    goog.findBasePath_();
    assertEquals('/path/to/', goog.basePath);
  } finally {
    // Restore context to respect other tests.
    goog.global = savedGoogGlobal;
  }
}

function testLoadBaseFromGlobalVariableOk() {
  var savedGoogGlobal = goog.global;
  try {
    goog.global = {};
    goog.global.document = {
      write: goog.nullFunction,
      getElementsByTagName:
          goog.functions.constant([{src: '/path/to/base.js?zx=5'}])
    };
    goog.global.CLOSURE_BASE_PATH = '/from/constant/';
    goog.findBasePath_();
    assertEquals(goog.global.CLOSURE_BASE_PATH, goog.basePath);
  } finally {
    // Restore context to respect other tests.
    goog.global = savedGoogGlobal;
  }
}

function testLoadBaseFromGlobalVariableDOMClobbered() {
  var savedGoogGlobal = goog.global;
  try {
    goog.global = {};
    goog.global.document = {
      write: goog.nullFunction,
      getElementsByTagName:
          goog.functions.constant([{src: '/path/to/base.js?zx=5'}])
    };
    // Make goog.global.CLOSURE_BASE_PATH an object with a toString, like
    // it would be if it were a DOM clobbered HTMLElement.
    goog.global.CLOSURE_BASE_PATH = {};
    goog.global.CLOSURE_BASE_PATH.toString = function() {
      return '/from/constant/';
    };
    goog.findBasePath_();
    assertEquals('/path/to/', goog.basePath);
  } finally {
    // Restore context to respect other tests.
    goog.global = savedGoogGlobal;
  }
}

function testLoadBaseFromCurrentScriptIgnoringOthers() {
  var savedGoogGlobal = goog.global;
  try {
    goog.global = {};
    goog.global.document = {
      write: goog.nullFunction,
      currentScript: {src: '/currentScript/base.js?zx=5'},
      getElementsByTagName:
          goog.functions.constant([{src: '/path/to/base.js?zx=5'}])
    };
    goog.findBasePath_();
    assertEquals('/currentScript/', goog.basePath);
  } finally {
    // Restore context to respect other tests.
    goog.global = savedGoogGlobal;
  }
}

function testAddDependencyModule() {
  var load = goog.testing.recordFunction();
  stubs.set(goog, 'writeScriptTag_', load);

  goog.addDependency('mod.js', ['testDep.mod'], [], true);
  goog.addDependency('empty.js', ['testDep.empty'], [], {});
  goog.addDependency('mod-goog.js', ['testDep.goog'], [], {'module': 'goog'});

  // To differentiate this call from the real one.
  var require = goog.require;

  var assertModuleLoad = function(module, args) {
    assertEquals(2, args.length);
    assertEquals('', args[0]);
    assertRegExp(
        '^goog\\.retrieveAndExec_\\(".*/' + module + '", true, false\\);$',
        args[1]);
  };

  require('testDep.mod');
  assertEquals(1, load.getCallCount());
  assertModuleLoad('mod.js', load.getCalls()[0].getArguments());

  require('testDep.empty');
  assertEquals(2, load.getCallCount());
  assertEquals(2, load.getCalls()[1].getArguments().length);
  assertRegExp('^.*/empty.js$', load.getCalls()[1].getArguments()[0]);
  assertUndefined(load.getCalls()[1].getArguments()[1]);

  require('testDep.goog');
  assertEquals(3, load.getCallCount());
  assertModuleLoad('mod-goog.js', load.getCalls()[2].getArguments());

  // Unset provided namespace so the test can be re-run.
  testDep = undefined;
}

function testAddDependencyEs6() {
  var script = null;
  var requireTranspilation = false;
  stubs.set(goog, 'needsTranspile_', function() {
    return requireTranspilation;
  });
  stubs.set(goog, 'writeScriptTag_', function(src, scriptText) {
    if (script != null) {
      throw new Error('Multiple scripts written');
    }
    script = scriptText;
  });

  goog.addDependency(
      'fancy.js', ['testDep.fancy'], [],
      {'lang': 'es6-impl', 'module': 'goog'});
  goog.addDependency('super.js', ['testDep.superFancy'], [], {'lang': 'es6'});

  // To differentiate this call from the real one.
  var require = goog.require;

  requireTranspilation = false;
  require('testDep.fancy');
  assertRegExp(
      /^goog\.retrieveAndExec_\(".*\/fancy\.js", true, false\);$/, script);
  script = null;

  requireTranspilation = true;
  require('testDep.superFancy');
  assertRegExp(
      /^goog\.retrieveAndExec_\(".*\/super\.js", false, true\);$/, script);

  // Unset provided namespace so the test can be re-run.
  testDep = undefined;
}

function testLateRequireProtection() {
  if (!document.readyState) return;
  var e = assertThrows(function() {
    // To differentiate this call from the real one.
    var require = goog.require;
    require('goog.ui.Component');
  });

  assertContains('after document load', e.message);
}

// Validate the behavior of goog.module when used from traditional files.
function testGoogLoadModuleByUrl() {
  if (goog.userAgent.IE && !goog.userAgent.isVersionOrHigher('10')) {
    // IE before 10 don't report an error.
    return;
  }

  stubs.set(goog, 'loadFileSync_', function(src) {
    return 'closure load file sync: ' + src;
  });

  // "goog.loadModuleByUrl" is not a general purpose code loader, it can
  // not be used to late load code.
  var err =
      assertThrows('loadModuleFromUrl should not hide failures', function() {
        goog.loadModuleFromUrl('bogus url');
      });
  assertContains('Cannot write "bogus url" after document load', err.message);
}
