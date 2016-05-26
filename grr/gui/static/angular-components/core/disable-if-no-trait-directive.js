'use strict';

goog.provide('grrUi.core.disableIfNoTraitDirective.DisableIfNoTraitController');
goog.provide('grrUi.core.disableIfNoTraitDirective.DisableIfNoTraitDirective');


goog.scope(function() {


/**
 * Controller for DisableIfNoTraitDirective.
 *
 * @constructor
 * @param {!angular.Attributes} $attrs
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.core.disableIfNoTraitDirective.DisableIfNoTraitController = function(
    $attrs, grrApiService) {
  /** @private {!angular.Attributes} */
  this.attrs_ = $attrs;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {string|undefined} */
  this.traitName_;

  this.attrs_.$observe('grrDisableIfNoTrait',
                       this.onTraitNameChange_.bind(this));
};
var DisableIfNoTraitController =
    grrUi.core.disableIfNoTraitDirective.DisableIfNoTraitController;


DisableIfNoTraitController.prototype.onTraitNameChange_ = function(newValue) {
  this.traitName_ = newValue;

  if (angular.isUndefined(newValue)) {
    this.attrs_.$set('disable', false);
  } else {
    this.grrApiService_.getCached('users/me').then(
        this.onUserInfo_.bind(this));
  }
};

DisableIfNoTraitController.prototype.onUserInfo_ = function(response) {
  var traitValue = false;

  var interfaceTraits = response['data']['value']['interface_traits'];
  if (angular.isDefined(interfaceTraits)) {
    if (angular.isDefined(interfaceTraits['value'][this.traitName_])) {
      traitValue = interfaceTraits['value'][this.traitName_]['value'];
    }
  }

  this.attrs_.$set('disabled', !traitValue);
};

/**
 * Directive for download links to aff4 streams.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.disableIfNoTraitDirective.DisableIfNoTraitDirective =
    function() {
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
grrUi.core.disableIfNoTraitDirective.DisableIfNoTraitDirective
    .directive_name = 'grrDisableIfNoTrait';


});  // goog.scope
