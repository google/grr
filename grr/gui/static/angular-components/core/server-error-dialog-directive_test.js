'use strict';

goog.module('grrUi.core.serverErrorDialogDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {coreModule} = goog.require('grrUi.core.core');


describe('server error dialog directive', () => {
  let $compile;
  let $rootScope;
  let $scope;


  beforeEach(module('/static/angular-components/core/server-error-dialog.html'));
  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
  }));

  const render = (message, traceBack) => {
    $scope.close = (() => {});
    $scope.message = message;
    $scope.traceBack = traceBack;

    const template =
        '<grr-server-error-dialog close="close()" message="message" trace-back="traceBack" />';
    const element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  it('should show a basic error message and traceback', () => {
    const message = 'Some error message';
    const traceBack = 'Some trace back';
    const element = render(message, traceBack);

    expect(element.find('.modal-header h3').text()).toBe(message);
    expect(element.find('.modal-body pre').text()).toBe(traceBack);
  });

  it('should operate on empty input', () => {
    const message = '';
    const traceBack = '';
    const element = render(message, traceBack);

    expect(element.find('.modal-header h3').text()).toBe(message);
    expect(element.find('.modal-body pre').text()).toBe(traceBack);
  });

  it('should call scope.close when clicking the X', () => {
    const message = '...';
    const traceBack = '...';
    const element = render(message, traceBack);

    spyOn($scope, 'close');
    browserTriggerEvent(element.find('.modal-header button'), 'click');
    expect($scope.close).toHaveBeenCalled();
  });


  it('should call scope.close when clicking the close button', () => {
    const message = '...';
    const traceBack = '...';
    const element = render(message, traceBack);

    spyOn($scope, 'close');
    browserTriggerEvent(element.find('.modal-footer button'), 'click');
    expect($scope.close).toHaveBeenCalled();
  });
});


exports = {};
