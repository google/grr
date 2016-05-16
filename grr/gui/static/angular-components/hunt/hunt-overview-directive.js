'use strict';

goog.provide('grrUi.hunt.huntOverviewDirective.HuntOverviewController');
goog.provide('grrUi.hunt.huntOverviewDirective.HuntOverviewDirective');

goog.scope(function() {



/**
 * Controller for HuntOverviewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.hunt.huntOverviewDirective.HuntOverviewController =
    function($scope, grrApiService, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntUrn;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @export {Object} */
  this.hunt;

  /** @export {Object} */
  this.huntSummary;

  this.scope_.$watch('huntUrn', this.onHuntUrnChange.bind(this));
};

var HuntOverviewController =
    grrUi.hunt.huntOverviewDirective.HuntOverviewController;


/**
 * Handles huntUrn attribute changes.
 * @export
 */
HuntOverviewController.prototype.onHuntUrnChange = function() {
  this.hunt = null;
  this.huntSummary = null;

  if (angular.isDefined(this.scope_.huntUrn)) {
    var huntUrnComponents = this.scope_.huntUrn.split('/');
    this.huntId = huntUrnComponents[huntUrnComponents.length - 1];

    this.hunt = null;
    this.huntSummary = null;

    this.grrApiService_.get('hunts/' + this.huntId).then(
        this.onHuntFetched.bind(this));
  }
};


/**
 * Called when hunt data was fetched.
 * @param {Object} response Response from the server.
 */
HuntOverviewController.prototype.onHuntFetched = function(response) {
  this.hunt = response.data;
  this.huntSummary = this.hunt.summary;
};


/**
 * Loads a 'hunt details' page after the 'View Hunt Details' link is clicked.
 */
HuntOverviewController.prototype.showHuntDetails = function() {
  var huntId = this.scope_.huntUrn.split('/')[2];
  this.grrRoutingService_.go('huntDetails', {huntId: huntId});
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
      huntUrn: '='
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
