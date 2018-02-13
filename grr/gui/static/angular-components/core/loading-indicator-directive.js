'use strict';

goog.module('grrUi.core.loadingIndicatorDirective');
goog.module.declareLegacyNamespace();



var LOADING_STARTED_EVENT_NAME = 'grrLoadingStartedEvent';
var LOADING_FINISHED_EVENT_NAME = 'grrLoadingFinishedEvent';


/**
 * Controller for LoadingIndicatorDirective.
 *
 * @constructor
 *
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 *
 * @ngInject
 */
const LoadingIndicatorController = function(
  $rootScope, $scope) {

  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {Array<Object>} */
  this.queue = [];

  /** @export {boolean} */
  this.queueIsEmpty = true;

  this.rootScope_.$on(LOADING_STARTED_EVENT_NAME,
      this.onLoadingStartedEvent_.bind(this));
  this.rootScope_.$on(LOADING_FINISHED_EVENT_NAME,
      this.onLoadingFinishedEvent_.bind(this));
};


/**
 * Enqueues loading events and shows the loading indicator, if necessary.
 * @param {?} event The event object
 * @param {Object} key The unique key to enqueue the event
 * @private
 */
LoadingIndicatorController.prototype.onLoadingStartedEvent_ = function(event, key) {
  this.queue.push(key);
  this.queueIsEmpty = this.queue.length === 0;
};

/**
 * Dequeues loading events and hides the loading indicator, if necessary.
 * @param {?} event The event object
 * @param {Object} key The unique key to deque the event
 * @throws {Object} Whenever the key is not found in the key, an exception is thrown.
 * @private
 */
LoadingIndicatorController.prototype.onLoadingFinishedEvent_ = function(event, key) {
  var index = this.queue.indexOf(key);
  if (index >= 0) {
    this.queue.splice(index, 1);
    this.queueIsEmpty = this.queue.length === 0;
  } else {
    // TODO(user): once all requests go through angular, we can enable stricter
    // fail behavior again.
    // throw new Error("Key not found: " + key);
  }
};


/**
 * Directive that shows a loading indicator in case loading events occur.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.LoadingIndicatorDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    template: '<div id="ajax_spinner" class="ajax_spinner" ng-hide="controller.queueIsEmpty">' +
              '    <img src="/static/images/ajax-loader.gif">' +
              '</div>',
    controller: LoadingIndicatorController,
    controllerAs: 'controller'
  };
};

var LoadingIndicatorDirective = exports.LoadingIndicatorDirective;


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
LoadingIndicatorDirective.directive_name = 'grrLoadingIndicator';

/**
 * Name of the loading started event
 *
 * @const
 * @export
 */
LoadingIndicatorDirective.loading_started_event_name = LOADING_STARTED_EVENT_NAME;

/**
 * Name of the loading started event
 *
 * @const
 * @export
 */
LoadingIndicatorDirective.loading_finished_event_name = LOADING_FINISHED_EVENT_NAME;

