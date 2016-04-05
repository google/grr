'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('server error dialog directive', function() {
  var $compile, $rootScope, $scope;

  beforeEach(module('/static/angular-components/core/server-error-dialog.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
  }));

  var render = function(message, traceBack) {
    $scope.close = function() {};
    $scope.message = message;
    $scope.traceBack = traceBack;

    var template = '<grr-server-error-dialog close="close()" message="message" trace-back="traceBack" />';
    var element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  it('should show a basic error message and traceback', function() {
    var message = 'Some error message';
    var traceBack = 'Some trace back';
    var element = render(message, traceBack);

    expect(element.find('.modal-header h3').text()).toBe(message);
    expect(element.find('.modal-body pre').text()).toBe(traceBack);
  });

  it('should operate on empty input', function() {
    var message = '';
    var traceBack = '';
    var element = render(message, traceBack);

    expect(element.find('.modal-header h3').text()).toBe(message);
    expect(element.find('.modal-body pre').text()).toBe(traceBack);
  });

  it('should call scope.close when clicking the X', function() {
    var message = '...';
    var traceBack = '...';
    var element = render(message, traceBack);

    spyOn($scope, 'close');
    browserTrigger(element.find('.modal-header button'), 'click');
    expect($scope.close).toHaveBeenCalled();
  });


  it('should call scope.close when clicking the close button', function() {
    var message = '...';
    var traceBack = '...';
    var element = render(message, traceBack);

    spyOn($scope, 'close');
    browserTrigger(element.find('.modal-footer button'), 'click');
    expect($scope.close).toHaveBeenCalled();
  });

});
