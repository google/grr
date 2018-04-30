'use strict';

goog.module('grrUi.sidebar.navDropdownDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for NavDropdownDirective.
 *
 * @constructor
 * @ngInject
 */
exports.NavDropdownController = function() {
  /** @type {!boolean} */
  this.isCollapsed = true;
};

var NavDropdownController = exports.NavDropdownController;


/**
 * Directive for the navDropdown.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.NavDropdownDirective = function() {
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
exports.NavDropdownDirective.directive_name = 'grrNavDropdown';
