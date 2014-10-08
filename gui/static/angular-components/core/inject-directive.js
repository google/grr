'use strict';

(function() {
  var module = angular.module('grr.inject.directive', []);

  // As to why we have to use grrInject and not ngTransclude sometimes, see:
  // https://github.com/angular/angular.js/issues/7874#issuecomment-47647528
  module.directive('grrInject', function($compile) {
    return {
      link: function($scope, $element, $attrs, controller, $transclude) {
        if (!$transclude) {
          throw minErr('ngTransclude')(
              'orphan',
              'Illegal use of ngTransclude directive in the template! ' +
                  'No parent directive that requires a transclusion found. ' +
                  'Element: {0}',
              startingTag($element));
        }

        var innerScope = $scope.$new();
        $transclude(innerScope, function(clone) {
          $element.empty();
          $element.append(clone);

          $element.on('$destroy', function() {
            innerScope.$destroy();
          });
        });
      }
    };
  });

})();
