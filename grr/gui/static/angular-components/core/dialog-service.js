'use strict';

goog.provide('grrUi.core.dialogService.DialogService');
goog.require('grrUi.core.utils.camelCaseToDashDelimited');

goog.scope(function() {


/**
 * Service for opening confirmation dialogs.
 *
 * @param {angular.Scope} $rootScope The Angular root scope.
 * @param {!angularUi.$modal} $modal Bootstrap UI modal service.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.dialogService.DialogService =
  function ($rootScope, $modal) {
    /** @private {angular.Scope} */
    this.rootScope_ = $rootScope;

    /** @private {!angularUi.$modal} */
    this.modal_ = $modal;
  };

var DialogService =
  grrUi.core.dialogService.DialogService;


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

  var modalInstance = this.modal_.open({
    template:
      '<grr-confirmation-dialog title="title" proceed="proceed()" >' +
      '  {$ message $}' +
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
 * @return {angular.$q.Promise} A promise indicating success or failure.
 * @export
 */
DialogService.prototype.openDirectiveDialog = function(directive, opt_params){
  var modalScope = this.rootScope_.$new();
  var paramString = '';

  // Convert camel-case directive name to dash-delimited tag name.
  var tagName = grrUi.core.utils.camelCaseToDashDelimited(directive);

  // Assign params to scope and build param string.
  if(angular.isDefined(opt_params)){
    angular.forEach(opt_params || {}, function(value, key) {
      modalScope[key] = opt_params[key];
      paramString += ' ' + key + '="' + key + '"';
    });
  }

  var template = '<' + tagName + ' ' + paramString + ' />';
  var modalInstance = this.modal_.open({
    template: template,
    scope: modalScope
  });
  return modalInstance.result;
};


});