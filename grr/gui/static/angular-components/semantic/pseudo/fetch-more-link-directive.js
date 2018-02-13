'use strict';

goog.module('grrUi.semantic.pseudo.fetchMoreLinkDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays 'fetch more' link.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.FetchMoreLinkDirective = function() {
  return {
    scope: {value: '='},
    link: function(scope) {
      // TODO(user): turn into controller
      scope.onClick = function(e) {
        scope.continuationShown = true;
        e.stopPropagation();  // onClick event should not be handleded by
                              // anything other than this, otherwise the click
                              // could be interpreted in the wrong way,
                              // e.g. page could be redirected.
      };
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/pseudo/' +
        'fetch-more-link.html',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.FetchMoreLinkDirective.directive_name = 'grrFetchMoreLink';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.FetchMoreLinkDirective.semantic_type = '__FetchMoreLink';
