'use strict';

goog.provide('grrUi.core.wizardFormDirective.WizardFormController');
goog.provide('grrUi.core.wizardFormDirective.WizardFormDirective');

goog.scope(function() {

/**
 * Controller for WizardFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.core.wizardFormDirective.WizardFormController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Array<Object>} */
  this.pages = [];

  /** @type {Object} */
  this.currentPage;

  /** @type {boolean} */
  this.isFirstPage;

  this.scope_.$watchCollection('controller.pages',
                               this.onPagesOrCurrentPageChange_.bind(this));
  this.scope_.$watch('controller.currentPage',
                     this.onPagesOrCurrentPageChange_.bind(this));
  this.scope_.$watch('controller.currentPage', function(newValue) {
    if (angular.isDefined(newValue)) {
      newValue.onShow();
    }
  }.bind(this));
};
var WizardFormController = grrUi.core.wizardFormDirective.WizardFormController;


/**
 * Handles changes of a current page.
 *
 * @private
 */
WizardFormController.prototype.onPagesOrCurrentPageChange_ = function() {
  this.isFirstPage = this.pages.indexOf(this.currentPage) == 0;
};

/**
 * Called when user presses 'Back' button.
 *
 * @export
 */
WizardFormController.prototype.back = function() {
  var index = this.pages.indexOf(this.currentPage);
  if (index == 0) {
    throw new Error('Can\'t go back from the first page.');
  }

  this.currentPage = this.pages[index - 1];
};

/**
 * Called when user presses 'Next' button.
 *
 * @export
 */
WizardFormController.prototype.next = function() {
  var index = this.pages.indexOf(this.currentPage);
  if (index < this.pages.length - 1) {
    this.currentPage = this.pages[index + 1];
  } else {
    this.scope_['onResolve']();
  }
};

/**
 * Called when 'x' button in the modal header is clicked.
 *
 * @export
 */
WizardFormController.prototype.reject = function() {
  this.scope_['onReject']();
};

/**
 * Registers a new page. Used by grr-wizard-form-page directives.
 *
 * @param {grrUi.core.wizardFormPageDirective.WizardFormPageController}
 *     pageController
 * @export
 */
WizardFormController.prototype.registerPage = function(pageController) {
  this.pages.push(pageController);

  if (angular.isUndefined(this.currentPage)) {
    this.currentPage = pageController;
  }
};


/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.wizardFormDirective.WizardFormDirective = function() {
  return {
    scope: {
      title: '@',
      onResolve: '&',
      onReject: '&'
    },
    restrict: 'E',
    transclude: true,
    templateUrl: '/static/angular-components/core/wizard-form.html',
    controller: WizardFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.wizardFormDirective.WizardFormDirective.directive_name =
    'grrWizardForm';

});  // goog.scope
