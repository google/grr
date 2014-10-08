'use strict';
(function() {
  var module = angular.module('grr.semanticProto.directive', []);

  module.directive('grrSemanticProto', function($compile) {
    return {
      scope: {
        value: '='
      },
      restrict: 'E',
      templateUrl: 'static/angular-components/semantic/semantic-proto.html',
      controller: function($scope, $element) {
        $scope.items = [];

        $scope.$watch('value', function() {
          $scope.items = [];
          for (var key in $scope.value.value) {
            if ($scope.value.descriptors !== undefined &&
                $scope.value.descriptors[key] !== undefined) {
              $scope.items.push({
                'value': $scope.value.value[key],
                'key': $scope.value.descriptors[key].friendly_name,
                'desc': $scope.value.descriptors[key].description
              });
            } else {
              $scope.items.push({'value': $scope.value.value[key],
                                 'key': key});
            }
          }
        });
      }
    };
  });
})();
