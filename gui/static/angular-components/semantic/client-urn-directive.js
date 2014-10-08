'use strict';
(function() {
  var module = angular.module('grr.clientUrn.directive',
                              ['grr.aff4.service',
                               'grr.semanticValue.directive']);

  module.directive('grrClientUrn', function(grrAff4Service) {
    return {
      scope: {
        value: '='
      },
      restrict: 'E',
      templateUrl: 'static/angular-components/semantic/client-urn.html',
      controller: function($scope, $element) {
        $scope.onLinkClick = function() {
          var hash = $.param({'main': 'HostInformation',
                              'c': $scope.value});
          grr.loadFromHash(hash);
        };

        $scope.client = {
          summary: null
        };

        // Show client information dialog when 'info' button is clicked.
        $scope.onButtonClick = function() {
          var dialog = $element.find('div[role=dialog]');
          dialog.modal();

          $scope.client.summary = null;
          grrAff4Service.get($scope.value, {
            'with_type_info': true,
            'with_descriptors': true}).then(function(response) {
            $scope.client.summary = response.data.summary;
          });
        };
      }
    };
  });
})();
