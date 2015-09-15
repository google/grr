'use strict';

goog.provide('grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageController');
goog.provide('grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective');

goog.scope(function() {

/**
 * Controller for ReviewPageDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
grrUi.hunt.newHuntWizard.reviewPageDirective
    .ReviewPageController = function(
        $scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {Object} */
  this.huntArgsDescriptor;


};
var ReviewPageController =
    grrUi.hunt.newHuntWizard.reviewPageDirective
    .ReviewPageController;

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.newHuntWizard.reviewPageDirective
    .ReviewPageDirective = function() {
  return {
    scope: {
      genericHuntArgs: '=',
      huntRunnerArgs: '='
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
grrUi.hunt.newHuntWizard.reviewPageDirective
    .ReviewPageDirective
    .directive_name = 'grrNewHuntReviewPage';

});  // goog.scope
