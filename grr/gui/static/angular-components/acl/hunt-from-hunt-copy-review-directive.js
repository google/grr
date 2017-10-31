'use strict';

goog.provide('grrUi.acl.huntFromHuntCopyReviewDirective.HuntFromHuntCopyReviewDirective');

goog.scope(function() {

/**
 * HuntFromHuntCopyReviewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.acl.huntFromHuntCopyReviewDirective.HuntFromHuntCopyReviewDirective = function() {
  return {
    scope: {
      sourceHunt: '=',
      newHunt: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/acl/hunt-from-hunt-copy-review.html'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.acl.huntFromHuntCopyReviewDirective.HuntFromHuntCopyReviewDirective.directive_name =
    'grrHuntFromHuntCopyReview';

});  // goog.scope
