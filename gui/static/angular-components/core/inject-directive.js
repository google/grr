'use strict';

goog.provide('grrUi.core.injectDirective.InjectDirective');

goog.scope(function() {



/**
 * As to why we have to use grrInject and not ngTransclude sometimes, see:
 * https://github.com/angular/angular.js/issues/7874#issuecomment-47647528
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.injectDirective.InjectDirective = function() {
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
};


/**
 * Directive name in Angular.
 */
grrUi.core.injectDirective.InjectDirective.directive_name = 'grrInject';

});  // goog.scope
