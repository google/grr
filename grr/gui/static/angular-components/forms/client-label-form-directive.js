'use strict';

goog.provide('grrUi.forms.clientLabelFormDirective.ClientLabelFormController');
goog.provide('grrUi.forms.clientLabelFormDirective.ClientLabelFormDirective');

goog.require('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {


var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/**
 * Controller for ClientLabelFormDirective.
 *
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.forms.clientLabelFormDirective.ClientLabelFormController =
    function(grrApiService) {
  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {*} */
  this.labelsList;

  /** @type {string} */
  this.clientLabel;

  /** @type {string} */
  this.formLabel;

  this.grrApiService_.get('/clients/labels').then(function(response) {
    this.labelsList = stripTypeInfo(response['data']['items']);
  }.bind(this));
};
var ClientLabelFormController =
    grrUi.forms.clientLabelFormDirective.ClientLabelFormController;


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
      formLabel: '=?'
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
