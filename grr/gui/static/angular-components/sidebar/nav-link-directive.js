'use strict';

goog.provide('grrUi.sidebar.navLinkDirective.NavLinkController');
goog.provide('grrUi.sidebar.navLinkDirective.NavLinkDirective');


goog.scope(function() {


/**
 * Controller for NavLinkDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.sidebar.navLinkDirective.NavLinkController = function(
    $scope, $element, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {grrUi.sidebar.navDropdownDirective.NavDropdownController} */
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

var NavLinkController =
    grrUi.sidebar.navLinkDirective.NavLinkController;



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
 * @constructor
 * @ngInject
 * @export
 */
grrUi.sidebar.navLinkDirective.NavLinkDirective = function() {
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
grrUi.sidebar.navLinkDirective.NavLinkDirective
    .directive_name = 'grrNavLink';


});  // goog.scope
