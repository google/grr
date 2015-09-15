'use strict';

goog.provide('grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormController');
goog.provide('grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective');


goog.scope(function() {

/**
 * Controller for Aff4AttributeFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.grrApiService_.get('/reflection/aff4/attributes').then(
      this.onGetAttributes_.bind(this));

  /** @type {!Array<string>} */
  this.allowedOptions = [];
};
var Aff4AttributeFormController =
    grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormController;


/**
 * Handles /clients/kb-fields response.
 *
 * @param {!Object} response
 * @private
 */
Aff4AttributeFormController.prototype.onGetAttributes_ = function(response) {
  this.allowedOptions = Object.keys(response['data']['attributes']).sort();

  if (this.allowedOptions.length > 0 && !this.scope_['value']['value']) {
    this.scope_['value']['value'] = this.allowedOptions[0];
  }
};


/**
 * Aff4AttributeFormDirective renders Aff4Attribute values.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective =
    function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '='
    },
    templateUrl: '/static/angular-components/forms/aff4-attribute-form.html',
    controller: Aff4AttributeFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective
    .directive_name = 'grrFormAff4Attribute';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective
    .semantic_type = 'AFF4Attribute';


});
