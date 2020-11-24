goog.module('grrUi.core.wizardFormPageDirective');
goog.module.declareLegacyNamespace();

const wizardFormDirective = goog.requireType('grrUi.core.wizardFormDirective');



/**
 * Controller for WizardFormPageDirective.
 * @unrestricted
 */
exports.WizardFormPageController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.Attributes} $attrs
   * @ngInject
   */
  constructor($scope, $attrs) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.Attributes} */
    this.attrs_ = $attrs;

    /** @type {!wizardFormDirective.WizardFormController} */
    this.formController;

    /** @type {string} */
    this.title;

    /** @type {string} */
    this.helpLink;

    /** @type {string} */
    this.prevButtonLabel = 'Back';

    /** @type {string} */
    this.nextButtonLabel = 'Next';

    /** @type {boolean} */
    this.noBackButton = false;

    /** @type {boolean} */
    this.isValid = true;

    this.scope_.$watch('title', function(newValue) {
      this.title = newValue;
    }.bind(this));

    this.scope_.$watch('prevButtonLabel', function(newValue) {
      if (angular.isDefined(newValue)) {
        this.prevButtonLabel = newValue;
      }
    }.bind(this));

    this.scope_.$watch('nextButtonLabel', function(newValue) {
      if (angular.isDefined(newValue)) {
        this.nextButtonLabel = newValue;
      }
    }.bind(this));

    this.scope_.$watch('noBackButton', function(newValue) {
      this.noBackButton = newValue;
    }.bind(this));

    this.scope_.$watch('isValid', function(newValue) {
      // Only update isValid if page has 'is-valid' attribute specified.
      if (angular.isDefined(this.attrs_['isValid'])) {
        this.isValid = newValue;
      }
    }.bind(this));

    this.scope_.$watch('helpLink', function(newValue) {
      this.helpLink = newValue;
    }.bind(this));
  }

  /**
   * Handles DOM 'show' event.
   *
   * @export
   */
  onShow() {
    this.scope_['onShow']();
  }
};
var WizardFormPageController = exports.WizardFormPageController;



/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.WizardFormPageDirective = function() {
  return {
    scope: {
      title: '@',
      helpLink: '@',
      prevButtonLabel: '@',
      nextButtonLabel: '@',
      noBackButton: '=?',
      isValid: '=?',
      onShow: '&'
    },
    restrict: 'E',
    transclude: true,
    templateUrl: '/static/angular-components/core/wizard-form-page.html',
    controller: WizardFormPageController,
    controllerAs: 'controller',
    require: '^grrWizardForm',
    link: function(scope, element, attrs, formController) {
      scope.controller.formController = formController;
      formController.registerPage(scope.controller);
    }
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.WizardFormPageDirective.directive_name = 'grrWizardFormPage';
