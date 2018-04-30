'use strict';

goog.module('grrUi.hunt.modifyHuntDialogDirective');
goog.module.declareLegacyNamespace();

const {AclDialogService} = goog.require('grrUi.acl.aclDialogService');
const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');
const {stripAff4Prefix} = goog.require('grrUi.core.utils');


/**
 * Controller for ModifyHuntDialogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!ApiService} grrApiService
 * @param {!AclDialogService} grrAclDialogService
 * @ngInject
 */
const ModifyHuntDialogController =
    function($scope, $q, grrApiService, grrAclDialogService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!AclDialogService} */
  this.grrAclDialogService_ = grrAclDialogService;

  /** @export {Object|undefined} */
  this.argsObj;

  this.scope_.$watch('huntId', this.onHuntIdChange_.bind(this));
};



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
            var message = response['data']['message'];

            if (response['status'] === 403) {
              var subject = response['data']['subject'];
              var huntId = stripAff4Prefix(subject).split('/')[1];

              this.grrAclDialogService_.openRequestHuntApprovalDialog(
                  huntId, message);
            }
            return this.q_.reject(message);
          }.bind(this));
};


/**
 * Displays a "Modify hunt" dialog.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.ModifyHuntDialogDirective = function() {
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
exports.ModifyHuntDialogDirective.directive_name = 'grrModifyHuntDialog';
