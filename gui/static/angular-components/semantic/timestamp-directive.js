'use strict';

goog.provide('grrUi.semantic.timestampDirective.TimestampDirective');

goog.require('grrUi.semantic.SemanticDirectivesRegistry');

goog.scope(function() {



/**
 * Directive that displays RDFDatetime values.
 *
 * @constructor
 * @param {Function} $filter Angular filter provider.
 * @ngInject
 * @export
 */
grrUi.semantic.timestampDirective.TimestampDirective = function($filter) {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<nobr ng-if="value">{{ formattedTimestamp }}</nobr>',
    controller: function($scope, $element) {
      $scope.$watch('value', function(newValue) {
        var timestamp;
        if (angular.isObject(newValue)) {
          timestamp = newValue.value / 1000;
        } else {
          timestamp = newValue / 1000;
        }
        $scope.formattedTimestamp = $filter('date')(
            timestamp, 'yyyy-MM-dd HH:mm:ss UTC', 'UTC');
      });
    }
  };
};


/**
 * Directive's name in Angular.
 */
grrUi.semantic.timestampDirective.TimestampDirective.directive_name =
    'grrTimestamp';

grrUi.semantic.SemanticDirectivesRegistry.registerDirective(
    'RDFDatetime',
    grrUi.semantic.timestampDirective.TimestampDirective);


});  // goog.scope
