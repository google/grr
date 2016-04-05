'use strict';

goog.provide('grrUi.hunt.huntStatusIconDirective.HuntStatusIconController');
goog.provide('grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective');


goog.scope(function() {


/**
 * Directive that displays hunt status icons for a given hunt.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective =
    function() {
      return {
        scope: {
          hunt: '='
        },
        restrict: 'E',
        templateUrl: '/static/angular-components/hunt/hunt-status-icon.html'
      };
    };


/**
 * Name of the directive in Angular.
 */
grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective
    .directive_name = 'grrHuntStatusIcon';


});  // goog.scope
