'use strict';

goog.module('grrUi.core.serverErrorButtonDirectiveTest');

const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('server error button directive', () => {
  const ERROR_EVENT_NAME = ServerErrorButtonDirective.error_event_name;
  let $compile;
  let $rootScope;
  let $scope;


  beforeEach(module('/static/angular-components/core/server-error-button.html'));
  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
  }));

  const render = () => {
    const template = '<grr-server-error-button />';
    const element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  const isVisible = (element) => !element.hasClass('ng-hide');

  it('should be hidden by default', () => {
    const element = render();
    expect(isVisible(element)).toBe(false);
  });

  it('should turn visible once a non-empty server error event is fired', () => {
    const element = render();
    expect(isVisible(element)).toBe(false);
    $scope.$apply(() => {
      $rootScope.$broadcast(ERROR_EVENT_NAME, {message: 'some event value'});
    });
    expect(isVisible(element)).toBe(true);
  });

  it('should ignore empty server error events', () => {
    const element = render();
    expect(isVisible(element)).toBe(false);
    $scope.$apply(() => {
      $rootScope.$broadcast(ERROR_EVENT_NAME);
    });
    expect(isVisible(element)).toBe(false);
  });
});


exports = {};
