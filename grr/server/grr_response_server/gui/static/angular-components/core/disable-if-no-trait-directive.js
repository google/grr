goog.module('grrUi.core.disableIfNoTraitDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Controller for DisableIfNoTraitDirective.
 * @unrestricted
 */
const DisableIfNoTraitController = class {
  /**
   * @param {!angular.Attributes} $attrs
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($attrs, grrApiService) {
    /** @private {!angular.Attributes} */
    this.attrs_ = $attrs;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {string|undefined} */
    this.traitName_;

    this.attrs_.$observe(
        'grrDisableIfNoTrait', this.onTraitNameChange_.bind(this));
  }

  /**
   * @param {?} newValue
   * @private
   */
  onTraitNameChange_(newValue) {
    this.traitName_ = newValue;

    if (angular.isUndefined(newValue)) {
      this.attrs_.$set('disable', false);
    } else {
      this.grrApiService_.getCached('users/me')
          .then(this.onUserInfo_.bind(this));
    }
  }

  /**
   * @param {Object} response
   * @private
   */
  onUserInfo_(response) {
    var traitValue = false;

    var interfaceTraits = response['data']['value']['interface_traits'];
    if (angular.isDefined(interfaceTraits)) {
      if (angular.isDefined(interfaceTraits['value'][this.traitName_])) {
        traitValue = interfaceTraits['value'][this.traitName_]['value'];
      }
    }

    this.attrs_.$set('disabled', !traitValue);
  }
};



/**
 * Directive for download links to aff4 streams.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.DisableIfNoTraitDirective = function() {
  return {
    scope: {},
    restrict: 'A',
    controller: DisableIfNoTraitController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.DisableIfNoTraitDirective.directive_name = 'grrDisableIfNoTrait';
