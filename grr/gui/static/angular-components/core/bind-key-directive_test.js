'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

var browserTriggerKeyDown = grrUi.tests.browserTriggerKeyDown;

describe('bind key directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector, _$interval_) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var render = function(callback, key) {
    $rootScope.callback = callback;

    var template = '<input type="text" grr-bind-key="callback()" key="' + key + '" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('calls the specified function on keydown', function(done) {
    var element = render(done, 13); // ENTER
    browserTriggerKeyDown(element, 13);
  });

  it('calls the specified function on keydown', function() {
    var callback = function(){
      fail('Callback should not be called');
    };
    var element = render(callback, 13); // ENTER
    browserTriggerKeyDown(element, 15); // Raise some other key.
  });
});
