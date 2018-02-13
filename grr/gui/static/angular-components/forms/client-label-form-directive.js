'use strict';

goog.module('grrUi.forms.clientLabelFormDirective');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');


/**
 * Controller for ClientLabelFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const ClientLabelFormController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {*} */
  this.labelsList;

  /** @type {string} */
  this.clientLabel;

  /** @type {string} */
  this.formLabel;

  /** @type {boolean} */
  this.hideEmptyOption;

  /** @type {string} */
  this.emptyOptionLabel;

  this.grrApiService_.get('/clients/labels').then(function(response) {
    this.labelsList = stripTypeInfo(response['data']['items']);

    this.scope_.$watch('controller.hideEmptyOption', function() {
      if (!this.clientLabel &&  // Handles all falsey values, including ''.
          this.hideEmptyOption &&
          this.labelsList.length > 0) {
        this.clientLabel = this.labelsList[0]['name'];
      }
    }.bind(this));
  }.bind(this));
};


/**
 * Initializes the client label form controller.
 */
ClientLabelFormController.prototype.$onInit = function() {
  this.hideEmptyOption = this.hideEmptyOption || false;
  this.emptyOptionLabel = this.emptyOptionLabel || '-- All clients --';
};

/**
 * Directive that displays a client label selector.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ClientLabelFormDirective = function() {
  return {
    scope: {
      clientLabel: '=',
      formLabel: '=?',
      hideEmptyOption: '=?',
      emptyOptionLabel: '=?'
    },
    bindToController: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/forms/client-label-form.html',
    controller: ClientLabelFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.ClientLabelFormDirective.directive_name = 'grrFormClientLabel';
