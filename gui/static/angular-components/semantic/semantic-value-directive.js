'use strict';

goog.provide('grrUi.semantic.semanticValueDirective.SemanticValueDirective');

goog.require('grrUi.semantic.SemanticDirectivesRegistry');

goog.scope(function() {

var SemanticDirectivesRegistry = grrUi.semantic.SemanticDirectivesRegistry;


/**
 * Converts camelCaseStrings to dash-delimited-strings.
 *
 * @param {string} directiveName String to be converted.
 * @return {string} Converted string.
 */
var camelCaseToDashDelimited = function(directiveName) {
  return directiveName.replace(/\W+/g, '-')
      .replace(/([a-z\d])([A-Z])/g, '$1-$2').toLowerCase();
};



/**
 * SemanticValueDirective renders given RDFValue by applying type-specific
 * renderers to its fields. It's assumed that RDFValue is fetched with
 * type info information.
 *
 * @constructor
 * @param {angular.$compile} $compile Angular's $compile service.
 * @ngInject
 * @export
 */
grrUi.semantic.semanticValueDirective.SemanticValueDirective = function(
    $compile) {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    link: function(scope, element, attrs) {
      scope.$watch('value', function() {
        if (scope.value === undefined || scope.value === null) {
          return;
        }

        if (angular.isArray(scope.value['mro'])) {
          var directive = SemanticDirectivesRegistry.findDirectiveForMro(
              scope.value['mro']);

          if (angular.isDefined(directive)) {
            element.append('<' +
                camelCaseToDashDelimited(directive.directive_name) +
                ' value="value" />');
          } else {
            element.text(scope.value.value.toString());
          }
        } else if (angular.isArray(scope.value)) {
          angular.forEach(scope.value, function(value, index) {
            if (angular.isArray(value['mro'])) {
              var directive = SemanticDirectivesRegistry.findDirectiveForMro(
                  value['mro']);
              if (angular.isDefined(directive)) {
                element.append('<' +
                    camelCaseToDashDelimited(directive.directive_name) +
                    ' value="value[' + index + ']" />');
              } else {
                element.text(value.value.toString());
              }
            } else {
              if (index > 0) {
                element.append(document.createTextNode(', '));
              }
              element.append(document.createTextNode(value.toString()));
            }
          });
        } else {
          element.text(scope.value.toString());
        }
        $compile(element.contents())(scope);
      });
    }
  };
};


/**
 * Directive's name in Angular.
 */
grrUi.semantic.semanticValueDirective.SemanticValueDirective.directive_name =
    'grrSemanticValue';

});  // goog.scope
