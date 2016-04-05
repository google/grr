'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');
goog.require('grrUi.tests.module');

describe('server error button directive', function() {
  var ERROR_EVENT_NAME = grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.error_event_name;
  var $compile, $rootScope, $scope;

  beforeEach(module('/static/angular-components/core/server-error-button.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
  }));

  var render = function() {
    var template = '<grr-server-error-button />';
    var element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  var isVisible = function(element) {
    return !element.hasClass('ng-hide');
  };

  it('should be hidden by default', function() {
    var element = render();
    expect(isVisible(element)).toBe(false);
  });

  it('should turn visible once a non-empty server error event is fired', function() {
    var element = render();
    expect(isVisible(element)).toBe(false);
    $scope.$apply(function() {
      $rootScope.$broadcast(ERROR_EVENT_NAME, {message: 'some event value'});
    });
    expect(isVisible(element)).toBe(true);
  });

  it('should ignore empty server error events', function() {
    var element = render();
    expect(isVisible(element)).toBe(false);
    $scope.$apply(function() {
      $rootScope.$broadcast(ERROR_EVENT_NAME);
    });
    expect(isVisible(element)).toBe(false);
  });

});
