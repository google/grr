'use strict';

goog.module('grrUi.core.serverErrorPreviewDirectiveTest');

const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('server error preview directive', () => {
  const ERROR_EVENT_NAME = ServerErrorButtonDirective.error_event_name;

  let $compile;
  let $rootScope;
  let $scope;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
  }));

  const render = () => {
    const template = '<grr-server-error-preview />';
    const element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  const isVisible = (element) => !element.hasClass('ng-hide');

  it('should be hidden by default', () => {
    const element = render();
    expect(isVisible(element)).toBe(false);
  });

  it('should show error message once a non-empty server error event is fired',
     () => {
       const errorMessage = 'some event value';
       const element = render();
       expect(isVisible(element)).toBe(false);
       $scope.$apply(() => {
         $rootScope.$broadcast(ERROR_EVENT_NAME, {message: errorMessage});
       });
       expect(isVisible(element)).toBe(true);
       expect(element.text().trim()).toBe(errorMessage);
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
