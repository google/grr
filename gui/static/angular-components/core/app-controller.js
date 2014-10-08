'use strict';
(function() {
  var module = angular.module('grr.app.controller',
                              ['grr.flowLog.directive',
                               'grr.huntErrors.directive',
                               'grr.huntLog.directive']);

  module.controller('GrrAppController', function($scope) {
  });
})();
