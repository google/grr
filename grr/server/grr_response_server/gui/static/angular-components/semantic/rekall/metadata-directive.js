'use strict';

goog.module('grrUi.semantic.rekall.metadataDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays rekall metadata messages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.MetadataDirective = function() {
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
exports.MetadataDirective.directive_name = 'grrRekallMetadata';
