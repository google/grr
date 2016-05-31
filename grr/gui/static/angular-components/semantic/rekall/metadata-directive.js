'use strict';

goog.provide('grrUi.semantic.rekall.metadataDirective.MetadataDirective');

goog.scope(function() {

/**
 * Directive that displays rekall metadata messages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.rekall.metadataDirective.MetadataDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/rekall/metadata.html',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.rekall.metadataDirective.MetadataDirective.directive_name =
    'grrRekallMetadata';

});  // goog.scope
