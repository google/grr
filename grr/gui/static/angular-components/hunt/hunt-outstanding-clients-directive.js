'use strict';

goog.provide('grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsController');
goog.provide('grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsDirective');

goog.scope(function() {


/**
 * Controller for HuntOutstandingClientsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsController = function(
    $scope) {
  /** @export {string} */
  this.outstandingClientsUrl;

  $scope.$watch('huntUrn', this.onHuntUrnChange_.bind(this));
};

var HuntOutstandingClientsController =
    grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsController;


/**
 * Handles huntUrn attribute changes.
 * @param {?string} huntUrn
 * @private
 */
HuntOutstandingClientsController.prototype.onHuntUrnChange_ = function(huntUrn) {
  if (!angular.isString(huntUrn)) {
    return;
  }

  var components = huntUrn.split('/');
  var huntId = components[components.length - 1];
  this.outstandingClientsUrl = '/hunts/' + huntId + '/clients/outstanding';
};


/**
 * Directive for displaying outstanding clients of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsDirective = function() {
  return {
    scope: {
      huntUrn: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-outstanding-clients.html',
    controller: HuntOutstandingClientsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsDirective.directive_name =
    'grrHuntOutstandingClients';

});  // goog.scope
