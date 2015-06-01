'use strict';

goog.provide('grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective');


goog.scope(function() {



/**
 * Directive that displays 'fetch more' link.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: 'List was truncated...'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective.directive_name =
    'grrFetchMoreLink';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective.semantic_type =
    'FetchMoreLink';


});  // goog.scope
