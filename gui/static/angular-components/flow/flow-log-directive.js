'use strict';
(function() {
  var module = angular.module('grr.flowLog.directive',
                              ['grr.collectionTable.directive']);

  module.directive('grrFlowLog', function() {
    return {
      scope: {
        flowUrn: '@'
      },
      restrict: 'E',
      templateUrl: 'static/angular-components/flow/flow-log.html',
      link: function(scope, element) {
        scope.$watch('flowUrn', function() {
          scope.logsUrn = scope.flowUrn + '/Logs';
        });
      }
    };
  });
})();
