'use strict';

goog.module('grrUi.core.loadingIndicatorDirectiveTest');

const {LoadingIndicatorDirective} = goog.require('grrUi.core.loadingIndicatorDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('loading indicator directive', () => {

  const LOADING_STARTED_EVENT_NAME =
      LoadingIndicatorDirective.loading_started_event_name;

  const LOADING_FINISHED_EVENT_NAME =
      LoadingIndicatorDirective.loading_finished_event_name;

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
    const template = '<grr-loading-indicator />';
    const element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  const isVisible =
      ((element) => !element.find('.ajax_spinner').hasClass('ng-hide'));

  const broadcast = (event, key) => {
    $rootScope.$apply(() => {
      $rootScope.$broadcast(event, key);
    });
  };

  it('should be hidden by default', () => {
    const element = render();
    expect(isVisible(element)).toBe(false);
  });

  it('should turn visible once a loading started event is fired', () => {
    const element = render();
    expect(isVisible(element)).toBe(false);
    broadcast(LOADING_STARTED_EVENT_NAME, 'some key');
    expect(isVisible(element)).toBe(true);
  });

  it('should turn invisible once a corresponding loading finished event is fired',
     () => {
       const element = render();
       expect(isVisible(element)).toBe(false);

       broadcast(LOADING_STARTED_EVENT_NAME, 'some key');
       expect(isVisible(element)).toBe(true);

       broadcast(LOADING_FINISHED_EVENT_NAME, 'some key');
       expect(isVisible(element)).toBe(false);
     });

  it('should ignore unrelated loading finished events', () => {
    const element = render();
    expect(isVisible(element)).toBe(false);

    broadcast(LOADING_STARTED_EVENT_NAME, 'some key');
    expect(isVisible(element)).toBe(true);

    broadcast(LOADING_FINISHED_EVENT_NAME, 'some other key');
    expect(isVisible(element)).toBe(true);

    // TODO(user): once all requests go through angular, we can throw error on
    // unrelated events. This code can be used to test this behavior:
    //    expect(function(){
    //      broadcast(LOADING_FINISHED_EVENT_NAME, 'some other key');
    //    }).toThrowError("Key not found: some other key");
    //    expect(isVisible(element)).toBe(true);
  });

  it('should turn invisible once all loading finished events occurred', () => {
    const element = render();
    expect(isVisible(element)).toBe(false);

    broadcast(LOADING_STARTED_EVENT_NAME, 'some key');
    broadcast(LOADING_STARTED_EVENT_NAME, 'some other key');
    broadcast(LOADING_STARTED_EVENT_NAME, 'one more key');
    expect(isVisible(element)).toBe(true);

    // finish events in arbitrary order
    broadcast(LOADING_FINISHED_EVENT_NAME, 'one more key');
    expect(isVisible(element)).toBe(true);

    broadcast(LOADING_FINISHED_EVENT_NAME, 'some key');
    expect(isVisible(element)).toBe(true);

    broadcast(LOADING_FINISHED_EVENT_NAME, 'some other key');
    expect(isVisible(element)).toBe(false); // all finished events occurred
  });
});

exports = {};
