'use strict';

goog.provide('grrUi.hunt.huntOverviewDirective.HuntOverviewController');
goog.provide('grrUi.hunt.huntOverviewDirective.HuntOverviewDirective');

goog.scope(function() {


/** @const {number} */
grrUi.hunt.huntOverviewDirective.AUTO_REFRESH_INTERVAL_S = 15;


/**
 * Controller for HuntOverviewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.hunt.huntOverviewDirective.HuntOverviewController = function(
    $scope, grrApiService, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntUrn;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @export {string} */
  this.huntId;

  /** @export {Object} */
  this.hunt;

  /** @private {!angular.$q.Promise|undefined} */
  this.pollPromise_;

  this.scope_.$on('$destroy', function() {
    this.grrApiService_.cancelPoll(this.pollPromise_);
  }.bind(this));

  this.scope_.$watch('huntUrn', this.startPolling_.bind(this));
};

var HuntOverviewController =
    grrUi.hunt.huntOverviewDirective.HuntOverviewController;


/**
 * Fetches hunt data;
 *
 * @private
 */
HuntOverviewController.prototype.startPolling_ = function() {
  this.grrApiService_.cancelPoll(this.pollPromise_);
  this.pollPromise_ = undefined;

  if (angular.isDefined(this.scope_['huntUrn'])) {
    var huntUrnComponents = this.scope_['huntUrn'].split('/');
    this.huntId = huntUrnComponents[huntUrnComponents.length - 1];

    var huntUrl = 'hunts/' + this.huntId;
    var interval = grrUi.hunt.huntOverviewDirective.AUTO_REFRESH_INTERVAL_S
        * 1000;

    this.pollPromise_ = this.grrApiService_.poll(huntUrl, interval);
    this.pollPromise_.then(
        undefined,
        undefined,
        function notify(response) {
          this.hunt = response['data'];
        }.bind(this));
  }
};


/**
 * Directive for displaying log records of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntOverviewDirective.HuntOverviewDirective = function() {
  return {
    scope: {
      huntUrn: '=',
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
grrUi.hunt.huntOverviewDirective.HuntOverviewDirective.directive_name =
    'grrHuntOverview';

});  // goog.scope
