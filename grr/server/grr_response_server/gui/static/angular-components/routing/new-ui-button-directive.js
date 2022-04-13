goog.module('grrUi.routing.newUiButtonDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');

/**
 * Controller for NewUiButtonDirective.
 * @unrestricted
 */
const NewUiButtonController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!routingService.RoutingService} grrRoutingService
   * @ngInject
   */
  constructor($scope, grrRoutingService) {
    /** @type {string} */
    this.url = grrRoutingService.getNewUiUrl();

    $scope.$root.$on('$stateChangeSuccess', () => {
      this.url = grrRoutingService.getNewUiUrl();
    });

    $scope.$root.$on('$locationChangeSuccess', () => {
      this.url = grrRoutingService.getNewUiUrl();
    });
  }
};

/**
 * Directive that displays a link to the new UI.
 *
 * @return {angular.Directive!} Directive definition object.
 * @ngInject
 * @export
 */
exports.NewUiButtonDirective = function() {
  return {
    scope: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/routing/new-ui-button.html',
    controller: NewUiButtonController,
    controllerAs: 'controller',
  };
};

const NewUiButtonDirective = exports.NewUiButtonDirective;

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
NewUiButtonDirective.directive_name = 'grrNewUiButton';
