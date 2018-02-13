'use strict';

goog.module('grrUi.core.dialogService');
goog.module.declareLegacyNamespace();

const {camelCaseToDashDelimited} = goog.require('grrUi.core.utils');



/**
 * Service for opening confirmation dialogs.
 *
 * @param {angular.Scope} $rootScope The Angular root scope.
 * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
 * @constructor
 * @ngInject
 * @export
 */
exports.DialogService = function($rootScope, $uibModal) {
  /** @private {angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angularUi.$uibModal} */
  this.uibModal_ = $uibModal;
};

var DialogService = exports.DialogService;


/**
 * Name of the service in Angular.
 */
DialogService.service_name = 'grrDialogService';

/**
 * Shows a confirmation dialog.
 *
 * @param {string} title The title of the dialog.
 * @param {string} message The message of the dialog.
 * @param {function()} proceed The proceed callback.
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
DialogService.prototype.openConfirmation = function(title, message, proceed){
  var modalScope = this.rootScope_.$new();
  modalScope.title = title;
  modalScope.message = message; //TODO(user): Evaluate markdown.
  modalScope.proceed = proceed;

  var modalInstance = this.uibModal_.open({
    template:
      '<grr-confirmation-dialog title="title" proceed="proceed()" >' +
      '  <div class="vertically-padded">{$ message $}</div>' +
      '</grr-confirmation-dialog>',
    scope: modalScope
  });

  return modalInstance.result;
};

/**
 * A generic method for opening dialogs implemented as directive with attributes.
 *
 * @param {string} directive The name of the dialog directive.
 * @param {Object=} opt_params The parameters for the dialog directive.
 * @param {Object=} opt_modalParams The parameters for the modal.
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
DialogService.prototype.openDirectiveDialog = function(directive, opt_params, opt_modalParams){
  var modalScope = this.rootScope_.$new();
  var paramString = '';

  // Convert camel-case directive name to dash-delimited tag name.
  var tagName = camelCaseToDashDelimited(directive);

  // Assign params to scope and build param string.
  if(angular.isDefined(opt_params)){
    angular.forEach(opt_params || {}, function(value, key) {
      modalScope[key] = opt_params[key];
      paramString += ' ' + camelCaseToDashDelimited(key) + '="' + key + '"';
    });
  }

  var template = '<' + tagName + ' ' + paramString +
      ' close="$close()" />';
  var modalParams = angular.extend({
    template: template,
    scope: modalScope
  }, opt_modalParams || {});
  var modalInstance = this.uibModal_.open(modalParams);
  return modalInstance.result;
};


