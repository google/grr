goog.module('grrUi.hunt.huntClientsDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for HuntClientsDirective.
 * @unrestricted
 */
const HuntClientsController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @export {string} */
    this.huntClientsUrl;

    /** @export {string} */
    this.clientType = 'completed';

    this.scope_.$watchGroup(
        ['huntId', 'controller.clientType'],
        this.onHuntIdOrClientTypeChange_.bind(this));
  }

  /**
   * Handles huntId attribute changes.
   *
   * @private
   */
  onHuntIdOrClientTypeChange_() {
    const huntId = this.scope_['huntId'];

    if (!angular.isString(huntId) || !angular.isString(this.clientType)) {
      return;
    }

    this.huntClientsUrl = '/hunts/' + huntId + '/clients/' + this.clientType;
  }
};



/**
 * Directive for displaying clients of a hunt with a given ID.
 *
 * @return {angular.Directive} Directive definition object.
 * @export
 */
exports.HuntClientsDirective = function() {
  return {
    scope: {huntId: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-clients.html',
    controller: HuntClientsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntClientsDirective.directive_name = 'grrHuntClients';
