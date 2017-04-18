'use strict';

goog.provide('grrUi.forms.clientLabelFormDirective.ClientLabelFormController');
goog.provide('grrUi.forms.clientLabelFormDirective.ClientLabelFormDirective');

goog.require('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {


var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/**
 * Controller for ClientLabelFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.forms.clientLabelFormDirective.ClientLabelFormController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
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
var ClientLabelFormController =
    grrUi.forms.clientLabelFormDirective.ClientLabelFormController;


ClientLabelFormController.prototype.$onInit = function() {
  this.hideEmptyOption = this.hideEmptyOption || false;
  this.emptyOptionLabel = this.emptyOptionLabel || '-- All clients --';
};

/**
 * Directive that displays a client label selector.
 *
 * @constructor
 * @ngInject
 * @export
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.clientLabelFormDirective.ClientLabelFormDirective = function() {
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
grrUi.forms.clientLabelFormDirective.ClientLabelFormDirective.directive_name =
    'grrFormClientLabel';


});  // goog.scope
