'use strict';

goog.module('grrUi.forms.aff4AttributeFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for Aff4AttributeFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const Aff4AttributeFormController = function(
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


/**
 * Handles /clients/kb-fields response.
 *
 * @param {!Object} response
 * @private
 */
Aff4AttributeFormController.prototype.onGetAttributes_ = function(response) {
  this.allowedOptions = [];
  angular.forEach(response['data']['items'], function(item) {
    this.allowedOptions.push(item['value']['name']['value']);
  }.bind(this));
  this.allowedOptions = this.allowedOptions.sort();

  if (this.allowedOptions.length > 0 && !this.scope_['value']['value']) {
    this.scope_['value']['value'] = this.allowedOptions[0];
  }
};


/**
 * Aff4AttributeFormDirective renders Aff4Attribute values.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.Aff4AttributeFormDirective = function() {
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
exports.Aff4AttributeFormDirective.directive_name = 'grrFormAff4Attribute';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.Aff4AttributeFormDirective.semantic_type = 'AFF4Attribute';
