goog.provide('grrUi.tests.browserTrigger');
goog.provide('grrUi.tests.module');
goog.provide('grrUi.tests.stubDirective');


/**
 * Module required to run GRR javascript tests in Karma.
 */
grrUi.tests.module = angular.module('grrUi.tests', []);

grrUi.tests.module.config(function($interpolateProvider) {
  $interpolateProvider.startSymbol('{$');
  $interpolateProvider.endSymbol('$}');
});

beforeEach(function() {
  module('grrUi.tests');
});


/**
 * Trigger a browser event on the given element.
 * The triggered event will be the simplest possible - e.g. for mouse events,
 * the coordinates will be 0, 0 and the related target element is null.
 * @param {!angular.jQuery} element
 * @param {string} eventType
 * @export
 */
grrUi.tests.browserTrigger = function(element, eventType) {
  if (element.injector) {
    element = element[0];
  } else if (element.prevObject) {
    element = element[0];
  }

  if (document.createEvent) {
    var event = document.createEvent('MouseEvents');
    // mouseenter and mouseleave must be edited because jqLite doesn't actually
    // listen on them - it listens on mouseover and mouseout and performs its
    // own logic to ignore the event if the related target is contained by the
    // target.
    if (eventType === 'mouseenter') {
      eventType = 'mouseover';
    }
    if (eventType === 'mouseleave') {
      eventType = 'mouseout';
    }
    event.initMouseEvent(eventType, true, true, window, 0, 0, 0, 0, 0, false,
                         false, false, false, 0, null);
    element.dispatchEvent(event);
  } else {
    element.fireEvent('on' + eventType);
  }
};

/**
 * Triggers a key down event on the given element.
 * @param {!angular.jQuery} element
 * @param {number} keyCode
 * @export
 */
grrUi.tests.browserTriggerKeyDown = function(element, keyCode) {
  var event = jQuery.Event("keypress");
  event.which = keyCode;
  element.trigger(event);
};

var directiveStubCounter = 0;

/**
 * Stub out a directive.
 *
 * This function creates a temporary test module and registers a stub
 * directive there with a high priority and terminal=true - this directive
 * will effectively block all other directives with a same name.
 *
 * Module with a fake directive has a unique name, so it won't get loaded
 * in other tests and therefore won't affect them.
 *
 * @param {string} directiveName
 * @export
 */
grrUi.tests.stubDirective = function(directiveName) {
  var moduleName = 'test.directives.stubs.' + directiveStubCounter;
  directiveStubCounter += 1;

  angular.module(moduleName, []).directive(directiveName,
                                           function() {
                                             return {
                                               priority: 100000,
                                               terminal: true
                                             };
                                           });

  beforeEach(module(moduleName));
};
