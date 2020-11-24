goog.module('grrUi.hunt.huntOverviewDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const routingService = goog.requireType('grrUi.routing.routingService');
const {huntExpirationTime} = goog.require('grrUi.hunt.utils');



/** @type {number} */
let AUTO_REFRESH_INTERVAL_MS = 15 * 1000;

/**
 * Sets the delay between automatic refreshes.
 *
 * @param {number} millis Interval value in milliseconds.
 * @export
 */
exports.setAutoRefreshInterval = function(millis) {
  AUTO_REFRESH_INTERVAL_MS = millis;
};


/**
 * Controller for HuntOverviewDirective.
 * @unrestricted
 */
const HuntOverviewController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @param {!routingService.RoutingService} grrRoutingService
   * @ngInject
   */
  constructor($scope, grrApiService, grrRoutingService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {string} */
    this.scope_.huntId;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!routingService.RoutingService} */
    this.grrRoutingService_ = grrRoutingService;

    /** @export {string} */
    this.huntId;

    /** @export {(!Object|undefined)} */
    this.hunt;

    /** @export {(!Object|undefined)} */
    this.huntExpirationTime;

    /** @private {!angular.$q.Promise|undefined} */
    this.pollPromise_;

    this.scope_.$on('$destroy', function() {
      this.grrApiService_.cancelPoll(this.pollPromise_);
    }.bind(this));

    this.scope_.$watch('huntId', this.startPolling_.bind(this));
  }

  /**
   * Fetches hunt data;
   *
   * @private
   */
  startPolling_() {
    this.grrApiService_.cancelPoll(this.pollPromise_);
    this.pollPromise_ = undefined;

    if (angular.isDefined(this.scope_['huntId'])) {
      this.huntId = this.scope_['huntId'];

      var huntUrl = 'hunts/' + this.huntId;
      var interval = AUTO_REFRESH_INTERVAL_MS;

      this.pollPromise_ = this.grrApiService_.poll(huntUrl, interval);
      this.pollPromise_.then(undefined, undefined, (response) => {
        const hunt = response['data'];
        this.hunt = hunt;
        this.huntExpirationTime = huntExpirationTime(hunt);
      });
    }
  }
};



/**
 * Directive for displaying log records of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HuntOverviewDirective = function() {
  return {
    scope: {
      huntId: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-overview.html',
    controller: HuntOverviewController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntOverviewDirective.directive_name = 'grrHuntOverview';
