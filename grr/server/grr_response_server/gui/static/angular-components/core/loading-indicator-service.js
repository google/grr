goog.module('grrUi.core.loadingIndicatorService');
goog.module.declareLegacyNamespace();

const {LoadingIndicatorDirective} = goog.require('grrUi.core.loadingIndicatorDirective');



const LOADING_STARTED_EVENT_NAME =
    LoadingIndicatorDirective.loading_started_event_name;

const LOADING_FINISHED_EVENT_NAME =
    LoadingIndicatorDirective.loading_finished_event_name;


/**
 * Service for communicating loading events,
 * @export
 * @unrestricted
 */
exports.LoadingIndicatorService = class {
  /**
   * @param {angular.Scope} $rootScope The Angular root scope.
   * @ngInject
   */
  constructor($rootScope) {
    /** @private {angular.Scope} */
    this.rootScope_ = $rootScope;

    /** @private {number} */
    this.key = 0;
  }

  /**
   * Creates a new unique key for the broadcasting a loading event.
   *
   * @return {number} A unique key to identify the loading event.
   * @private
   */
  getNextKey_() {
    return this.key++;
  }

  /**
   * Broadcasts a loading started event to show the loading indicator.
   *
   * @return {number} A unique key to identify the loading event.
   */
  startLoading() {
    const key = this.getNextKey_();
    this.rootScope_.$broadcast(LOADING_STARTED_EVENT_NAME, key);
    return key;
  }

  /**
   * Broadcasts a loading finished event to hide the loading indicator.
   * @param {number} key The key of the corresponding loading started event.
   */
  stopLoading(key) {
    this.rootScope_.$broadcast(LOADING_FINISHED_EVENT_NAME, key);
  }
};

const LoadingIndicatorService = exports.LoadingIndicatorService;


/**
 * Name of the service in Angular.
 */
LoadingIndicatorService.service_name = 'grrLoadingIndicatorService';
