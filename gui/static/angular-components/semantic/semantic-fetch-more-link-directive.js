'use strict';

goog.provide('grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective');

goog.require('grrUi.semantic.SemanticDirectivesRegistry');


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
 */
grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective.directive_name =
    'grrFetchMoreLink';

grrUi.semantic.SemanticDirectivesRegistry.registerDirective(
    'FetchMoreLink',
    grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective);


});  // goog.scope
