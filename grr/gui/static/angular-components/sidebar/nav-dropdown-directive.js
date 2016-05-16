'use strict';

goog.provide('grrUi.sidebar.navDropdownDirective.NavDropdownController');
goog.provide('grrUi.sidebar.navDropdownDirective.NavDropdownDirective');


goog.scope(function() {


/**
 * Controller for NavDropdownDirective.
 *
 * @constructor
 * @ngInject
 */
grrUi.sidebar.navDropdownDirective.NavDropdownController = function() {
  /** @type {!boolean} */
  this.isCollapsed = true;
};

var NavDropdownController =
    grrUi.sidebar.navDropdownDirective.NavDropdownController;


/**
 * Directive for the navDropdown.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.sidebar.navDropdownDirective.NavDropdownDirective =
    function() {
  return {
    scope: {
      title: '@'
    },
    restrict: 'A',
    transclude: true,
    templateUrl: '/static/angular-components/sidebar/nav-dropdown.html',
    controller: NavDropdownController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.sidebar.navDropdownDirective.NavDropdownDirective
    .directive_name = 'grrNavDropdown';


});  // goog.scope
