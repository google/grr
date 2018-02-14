'use strict';

goog.module('grrUi.acl.huntFromHuntCopyReviewDirective');
goog.module.declareLegacyNamespace();



/**
 * HuntFromHuntCopyReviewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.HuntFromHuntCopyReviewDirective = function() {
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
exports.HuntFromHuntCopyReviewDirective.directive_name =
    'grrHuntFromHuntCopyReview';
