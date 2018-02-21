// TODO(hanuszczak): Figure out why this file cannot be named `tests.js`.
goog.provide('grrUi.tests');
goog.provide('grrUi.tests.browserTriggerEvent');
goog.provide('grrUi.tests.browserTriggerKeyDown');
goog.provide('grrUi.tests.stubDirective');
goog.provide('grrUi.tests.stubTranscludeDirective');
goog.provide('grrUi.tests.stubUiTrait');
goog.provide('grrUi.tests.testsModule');


/**
 * Module required to run GRR javascript tests in Karma.
 */
grrUi.tests.testsModule = angular.module('grrUi.tests', ['ng', 'ui.bootstrap']);

var $animate;
beforeEach(module('ngAnimateMock'));

grrUi.tests.testsModule.config(function($interpolateProvider, $qProvider,
                                   $uibModalProvider) {
  $interpolateProvider.startSymbol('{$');
  $interpolateProvider.endSymbol('$}');

  $qProvider.errorOnUnhandledRejections(false);

  $uibModalProvider.options.animation = false;
}).run(function($injector) {
  $animate = $injector.get('$animate');
});


beforeEach(function() {
  module('grrUi.tests');

  // We provide a general mock for grrRoutingService here. This mock can be
  // injected in any test via $inject. We do this since we want to test
  // directives in isolation without routing. Furthermore, the grrUi.routing
  // module runs init routines during configuration. We do not want them to
  // interfere with directive tests.
  var grrRoutingServiceMock = {
    go: function(state, params) {},
    href: function(state, params) { return '#test/href'; },
    uiOnParamsChanged: function(scope, paramNames, callback) {},
    onStateChange: function(scope, callback) {}
  };
  module(function($provide) {
    $provide.factory('grrRoutingService', function() {
      return grrRoutingServiceMock;
    });
  });
});

/**
 * Trigger a browser event on the given element.
 * The triggered event will be the simplest possible - e.g. for mouse events,
 * the coordinates will be 0, 0 and the related target element is null.
 * @param {!angular.jQuery} element
 * @param {string} eventType
 * @export
 */
grrUi.tests.browserTriggerEvent = function(element, eventType) {
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

  // True is for 'hideErrors' for cases when no animations are pending.
  $animate.flush(true);
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

  angular.module(moduleName, []).directive(
      directiveName,
      function() {
        return {
          priority: 100000 + directiveStubCounter,
          terminal: true
        };
      });

  beforeEach(module(moduleName));
};


/**
 * Stub out a transclude directive.
 *
 * This function stubs the directive exactly as stubDirective does, but
 * it declares the stub as a 'transclude' directive, thus rendering
 * everything between the the stubbed directive tags. Useful when
 * we need to stub directive "foo", but we care about the transcluded
 * directive "bar":
 * <foo>
 *  <bar></bar>
 * </foo>
 *
 * @param {string} directiveName
 * @export
 */
grrUi.tests.stubTranscludeDirective = function(directiveName) {
  var moduleName = 'test.directives.stubs.' + directiveStubCounter;
  directiveStubCounter += 1;

  angular.module(moduleName, []).directive(
      directiveName,
      function() {
        return {
          restrict: 'E',
          scope: {},
          transclude: true,
          priority: 100000 + directiveStubCounter,
          terminal: true,
          link: function($scope, $element, $attrs, controller, $transclude) {
            function ngTranscludeCloneAttachFn(clone) {
              if (clone.length) {
                $element.empty();
                $element.append(clone);
              }
            }
            $transclude(ngTranscludeCloneAttachFn, null, null);
          }
        };
      });

  beforeEach(module(moduleName));
};


/**
 * Stub out a GRR UI trait (see grr-disable-if-no-trait directive).
 *
 * This function stubs out the trait, so that UI pieces that depend on this
 * trait treat it as "enabled" in the test.
 *
 * @param {string} traitName
 * @export
 */
grrUi.tests.stubUiTrait = function(traitName) {
  beforeEach(inject(function($injector) {
    const $q = $injector.get('$q');
    const grrApiService = $injector.get('grrApiService');

    var deferred = $q.defer();
    var response = {
      data: {
        value: {
          interface_traits: {
            value: {}
          }
        }
      }
    };
    response['data']['value']['interface_traits']['value'][traitName] = {
      value: true
    };
    deferred.resolve(response);

    var currentImpl = grrApiService.getCached;
    spyOn(grrApiService, 'getCached').and.callFake(function(url, params) {
      if (url == 'users/me') {
        return deferred.promise;
      } else {
        return currentImpl(url, params);
      }
    });
  }));
};
