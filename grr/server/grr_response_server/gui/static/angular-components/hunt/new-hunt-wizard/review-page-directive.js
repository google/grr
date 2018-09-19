goog.module('grrUi.hunt.newHuntWizard.reviewPageDirective');
goog.module.declareLegacyNamespace();


/**
 * Controller for ReviewPageDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
const ReviewPageController = function($scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @public {boolean} */
  this.isRapidHuntEligible = false;

  // Using null as a default here since "undefined" is one of the possible
  // client rate values that we may need to store in this variable. Hence,
  // we want to distinguish "unset" and "set to undefined" states.
  this.oldClientRate_ = null;

  this.scope_.$watch('controller.isRapidHuntEligible',
                     this.onRapidHuntEligibilityChange_.bind(this));
};


/**
 * Callback called when controller's isRapidHuntEligible attribute changes.
 *
 * @param {boolean} newValue New attribute value.
 * @private
 */
ReviewPageController.prototype.onRapidHuntEligibilityChange_ = function(
    newValue) {
  if (newValue) {
    this.grrReflectionService_.getRDFValueDescriptor('float').then((desc) => {
      const clientRate = angular.copy(desc['default']);

      this.oldClientRate_ = this.scope_['createHuntArgs']['value'][
        'hunt_runner_args']['value']['client_rate'];
      this.scope_['createHuntArgs']['value']['hunt_runner_args'][
        'value']['client_rate'] = clientRate;
    });
  } else if (this.oldClientRate_ !== null) {
    this.scope_['createHuntArgs']['value']['hunt_runner_args'][
      'value']['client_rate'] = this.oldClientRate_;
    this.oldClientRate_ = null;
  }
};

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ReviewPageDirective = function() {
  return {
    scope: {
      createHuntArgs: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'review-page.html',
    controller: ReviewPageController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ReviewPageDirective.directive_name = 'grrNewHuntReviewPage';
