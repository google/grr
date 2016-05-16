'use strict';

goog.provide('grrUi.hunt.huntsViewDirective.HuntsViewController');
goog.provide('grrUi.hunt.huntsViewDirective.HuntsViewDirective');

goog.scope(function() {


/**
 * Controller for HuntsViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.hunt.huntsViewDirective.HuntsViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.selectedHuntUrn;

  /** @type {string} */
  this.tab;

  this.scope_.$watchGroup(['controller.selectedHuntUrn', 'controller.tab'],
      this.onSelectionChange_.bind(this));

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, ['huntId', 'tab'],
      this.onParamsChange_.bind(this));
};
var HuntsViewController =
    grrUi.hunt.huntsViewDirective.HuntsViewController;


/**
 * Handles changes to the state params.
 *
 * @param {Array} newValues The new values for the watched params.
 * @param {Object=} opt_stateParams A dictionary of all state params and their values.
 * @private
 */
HuntsViewController.prototype.onParamsChange_ = function(newValues, opt_stateParams) {
  if (opt_stateParams['huntId']) {
    this.selectedHuntUrn = 'aff4:/hunts/' + opt_stateParams['huntId'];
  }
  this.tab = opt_stateParams['tab'];
};

/**
 * Handles changes to the selected hunt or tab.
 *
 * @private
 */
HuntsViewController.prototype.onSelectionChange_ = function() {
  if (angular.isDefined(this.selectedHuntUrn)) {
    var huntId = this.selectedHuntUrn.split('/')[2];
    this.grrRoutingService_.go('hunts', {huntId: huntId, tab: this.tab});
  }
};


/**
 * HuntsViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.hunt.huntsViewDirective.HuntsViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    templateUrl: '/static/angular-components/hunt/hunts-view.html',
    controller: HuntsViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntsViewDirective.HuntsViewDirective.directive_name =
    'grrHuntsView';

});  // goog.scope
