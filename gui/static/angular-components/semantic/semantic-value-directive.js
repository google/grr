'use strict';
(function() {
  var module = angular.module('grr.semanticValue.directive',
                              ['grr.semanticProto.directive']);

  // grr-semantic-value directive renders given RDFValue by applying
  // type-specific renderers to its fields. It's assumed that RDFValue
  // is fetched with type info information.
  module.directive('grrSemanticValue', function($compile) {
    return {
      scope: {
        value: '='
      },
      restrict: 'E',
      controller: function($scope, $element) {
      },
      link: function(scope, element, attrs) {
        scope.$watch('value', function() {
          $(element).html('');
          if (scope.value == null) {
            return;
          }

          if (scope.value.mro !== undefined) {
            if (scope.value.mro.indexOf('RDFProtoStruct') != -1) {
              $(element).append('<grr-semantic-proto value="value" />');
            } else if (scope.value.mro.indexOf('ClientURN') != -1) {
              $(element).append('<grr-client-urn value="value.value" />');
            } else {
              element.append(scope.value.value.toString());
            }
          } else {
            element.append(scope.value.toString());
          }
          $compile($(element).contents())(scope);
        });
      }
    };
  });
})();
