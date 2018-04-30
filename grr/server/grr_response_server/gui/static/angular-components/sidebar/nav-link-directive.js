'use strict';

goog.module('grrUi.sidebar.navLinkDirective');
goog.module.declareLegacyNamespace();

const {NavDropdownController} = goog.require('grrUi.sidebar.navDropdownDirective');
const {RoutingService} = goog.require('grrUi.routing.routingService');


/**
 * Controller for NavLinkDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!RoutingService} grrRoutingService
 * @ngInject
 */
const NavLinkController = function(
    $scope, $element, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {NavDropdownController} */
  this.navDropdownController;

  /** @type {boolean} */
  this.isActive = false;

  /** @type {string} */
  this.href;

  this.scope_.$watchGroup(['state', 'params'],
                          this.onStateOrParamsChange_.bind(this));

  this.grrRoutingService_.onStateChange(this.scope_,
      this.applyActiveState_.bind(this));
};


/**
 * @private
 */
NavLinkController.prototype.onStateOrParamsChange_ = function() {
  this.href = '#';
  if (angular.isDefined(this.scope_['state'])) {
    this.href = this.grrRoutingService_.href(this.scope_['state'],
                                             this.scope_['params']);
  }
};


/**
 * Opens a link by calling the specific renderer.
 *
 * @export
 */
NavLinkController.prototype.openLink = function(event) {
  event.preventDefault();

  if (this.scope_['disabled']) {
    return;
  }
  this.grrRoutingService_.go(this.scope_['state'], this.scope_['params']);
};

/**
 * Called whenever the active state changes. If the state of this instance is
 * the active one, a class is applied to the current element.
 *
 * @param {string} activeState The name of the active state.
 * @private
 */
NavLinkController.prototype.applyActiveState_ = function(activeState) {
  this.isActive = (activeState === this.scope_['state']);

  if (this.isActive) {
    this.element_.addClass('active');
    if (this.navDropdownController) {
      this.navDropdownController.isCollapsed = false;
    }
  } else {
    this.element_.removeClass('active');
  }
};

/**
 * Directive for the navLink.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.NavLinkDirective = function() {
  return {
    scope: {
      state: '@',
      params: '=?',
      disabled: '=?'
    },
    restrict: 'A',
    require: '?^grrNavDropdown',
    transclude: true,
    templateUrl: '/static/angular-components/sidebar/nav-link.html',
    controller: NavLinkController,
    controllerAs: 'controller',
    link: function(scope, elem, attr, navDropdownController) {
      scope.controller.navDropdownController = navDropdownController;
    }
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.NavLinkDirective.directive_name = 'grrNavLink';
