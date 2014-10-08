'use strict';
(function() {
  var module = angular.module('grr.huntErrors.directive',
                              ['grr.clientUrn.directive',
                               'grr.collectionTable.directive']);

  module.directive('grrHuntErrors', function() {
    return {
      scope: {
        huntUrn: '@'
      },
      restrict: 'E',
      templateUrl: 'static/angular-components/hunt/hunt-errors.html',
      link: function(scope, element) {
        scope.$watch('huntUrn', function() {
          scope.errorsUrn = scope.huntUrn + '/ErrorClients';
        });
      }
    };
  });
})();
