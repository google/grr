goog.provide('grrUi.tests.browserTrigger');
goog.provide('grrUi.tests.module');


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
 * @param {angular.jqLite} element
 * @param {string} eventType
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
