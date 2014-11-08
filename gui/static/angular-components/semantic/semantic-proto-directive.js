'use strict';

goog.provide('grrUi.semantic.semanticProtoDirective.SemanticProtoDirective');

goog.scope(function() {


/**
 * Builds a list of items to display from the given value. If value
 * has type descriptors, friendly names will be used as keys and
 * description will be filled in.
 *
 * @param {!Object} value Value to be converted to an array of items.
 * @private
 */
grrUi.semantic.semanticProtoDirective.buildItems_ = function(value) {
  var items = [];

  for (var key in value.value) {
    if (value.descriptors !== undefined &&
        value.descriptors[key] !== undefined) {
      items.push({
        'value': value.value[key],
        'key': value.descriptors[key].friendly_name,
        'desc': value.descriptors[key].description
      });
    } else {
      items.push({'value': this.scope.value.value[key],
        'key': key});
    }
  }

  return items;
};



/**
 * Directive that displays semantic proto fetched from the server.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.semanticProtoDirective.SemanticProtoDirective = function() {
  return {
    scope: {
      value: '='
    },
    link: function($scope) {
      $scope['items'] = [];
      $scope.$watch('value', function() {
        if (angular.isObject($scope['value'])) {
          $scope['items'] = grrUi.semantic.semanticProtoDirective.buildItems_(
              $scope['value']);
        } else {
          $scope['items'] = [];
        }
      });
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/semantic/semantic-proto.html'
  };
};


/**
 * Name of the directive in Angular.
 */
grrUi.semantic.semanticProtoDirective.SemanticProtoDirective.directive_name =
    'grrSemanticProto';

});  // goog.scope
