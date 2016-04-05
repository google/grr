'use strict';

goog.require('grrUi.core.loadingIndicatorDirective.LoadingIndicatorDirective');
goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

describe('loading indicator directive', function() {

  var LoadingIndicatorDirective =
      grrUi.core.loadingIndicatorDirective.LoadingIndicatorDirective;

  var LOADING_STARTED_EVENT_NAME =
      LoadingIndicatorDirective.loading_started_event_name;

  var LOADING_FINISHED_EVENT_NAME =
      LoadingIndicatorDirective.loading_finished_event_name;

  var $compile, $rootScope, $scope;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
  }));

  var render = function() {
    var template = '<grr-loading-indicator />';
    var element = $compile(template)($scope);
    $scope.$apply();
    return element;
  };

  var isVisible = function(element){
    return !element.find('.ajax_spinner').hasClass('ng-hide');
  };

  var broadcast = function(event, key){
    $rootScope.$apply(function() {
      $rootScope.$broadcast(event, key);
    });
  };

  it('should be hidden by default', function() {
    var element = render();
    expect(isVisible(element)).toBe(false);
  });

  it('should turn visible once a loading started event is fired', function() {
    var element = render();
    expect(isVisible(element)).toBe(false);
    broadcast(LOADING_STARTED_EVENT_NAME, 'some key');
    expect(isVisible(element)).toBe(true);
  });

  it('should turn invisible once a corresponding loading finished event is fired', function() {
    var element = render();
    expect(isVisible(element)).toBe(false);

    broadcast(LOADING_STARTED_EVENT_NAME, 'some key');
    expect(isVisible(element)).toBe(true);

    broadcast(LOADING_FINISHED_EVENT_NAME, 'some key');
    expect(isVisible(element)).toBe(false);
  });

  it('should ignore unrelated loading finished events', function() {
    var element = render();
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

  it('should turn invisible once all loading finished events occured', function() {
    var element = render();
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
    expect(isVisible(element)).toBe(false); // all finished events occured
  });

});