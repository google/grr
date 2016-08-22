'use strict';

goog.provide('grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogController');
goog.provide('grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogDirective');


goog.require('grrUi.core.apiService.stripTypeInfo');


goog.scope(function() {


var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;


/**
 * Controller for ModifyHuntDialogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogController =
    function($scope, $q, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object|undefined} */
  this.argsObj;

  this.scope_.$watch('huntId', this.onHuntIdChange_.bind(this));
};

var ModifyHuntDialogController =
    grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogController;


/**
 * Handles changes in huntId binding.
 *
 * @param {string} newValue New huntId value.
 *
 * @private
 */
ModifyHuntDialogController.prototype.onHuntIdChange_ = function(newValue) {
  this.argsObj = undefined;

  if (angular.isString(newValue)) {
    this.grrApiService_.get('/hunts/' + newValue).then(function(response) {
      var hunt = response['data'];
      this.argsObj = {
        type: 'ApiModifyHuntArgs',
        value: {
        }
      };

      angular.forEach(['client_limit', 'client_rate', 'expires'], function(k) {
        var v = hunt['value'][k];

        if (v) {
          this.argsObj['value'][k] = angular.copy(v);
        }
      }.bind(this));
    }.bind(this));
  }
};


/**
 * Callback called by grr-confirmation-dialog when "Proceed" button is clicked.
 *
 * @return {!angular.$q.Promise}
 *
 * @export
 */
ModifyHuntDialogController.prototype.proceed = function() {
  var request = /** @type {Object} */ (stripTypeInfo(this.argsObj));
  return this.grrApiService_.patch(
      '/hunts/' + this.scope_['huntId'], request).then(
          function success() {
            return 'Hunt modified successfully!';
          }.bind(this),
          function failure(response) {
            if (response['status'] === 403) {
              // TODO(user): migrate from using grr.publish to using
              // Angular services.
              grr.publish('unauthorized',
                          response['data']['subject'],
                          response['data']['message']);
            }

            return this.q_.reject(response['data']['message']);
          }.bind(this));
};


/**
 * Displays a "Modify hunt" dialog.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogDirective = function() {
  return {
    scope: {
      huntId: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/modify-hunt-dialog.html',
    controller: ModifyHuntDialogController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogDirective.directive_name =
    'grrModifyHuntDialog';

});  // goog.scope
