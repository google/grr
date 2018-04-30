'use strict';

goog.module('grrUi.hunt.newHuntWizard.copyFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for CopyFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const CopyFormController =
    function($scope, grrReflectionService, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Object} */
  this.createHuntArgs;

  /** @type {Object} */
  this.createHuntArgsDescriptor;

  this.grrReflectionService_.getRDFValueDescriptor('ApiCreateHuntArgs', true).then(function(descriptor) {
    this.createHuntArgsDescriptor = descriptor['ApiCreateHuntArgs'];
    this.huntRefDescriptor = descriptor['ApiHuntReference'];

    this.scope_.$watch('huntId', this.onHuntIdChange_.bind(this));
  }.bind(this));
};


/**
 * Handles huntId attribute changes.
 *
 * @private
 */
CopyFormController.prototype.onHuntIdChange_ = function() {
  if (angular.isDefined(this.scope_['huntId'])) {
    this.huntId = this.scope_['huntId'];

    this.grrApiService_.get('hunts/' + this.huntId).then(
        this.onHuntFetched_.bind(this));
  }
};

/**
 * Called when hunt data was fetched.
 *
 * @param {Object} response Response from the server.
 * @private
 */
CopyFormController.prototype.onHuntFetched_ = function(response) {
  var hunt = response['data'];

  this.createHuntArgs = angular.copy(this.createHuntArgsDescriptor['default']);
  this.createHuntArgs['value']['flow_name'] =
      angular.copy(hunt['value']['flow_name']);
  this.createHuntArgs['value']['flow_args'] =
      angular.copy(hunt['value']['flow_args']);

  var huntRunnerArgs = this.createHuntArgs['value']['hunt_runner_args'] =
      angular.copy(hunt['value']['hunt_runner_args']);
  if (angular.isDefined(huntRunnerArgs['value']['description'])) {
    huntRunnerArgs['value']['description']['value'] += ' (copy)';
  }

  this.createHuntArgs['value']['original_hunt'] =
       angular.copy(this.huntRefDescriptor['default']);
  this.createHuntArgs['value']['original_hunt']['value']['hunt_id'] =
       hunt['value']['hunt_id'];
};


/**
 * Displays a new hunt wizard form with fields prefilled from another hunt.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.CopyFormDirective = function() {
  return {
    scope: {
      huntId: '=',
      onResolve: '&',
      onReject: '&'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'copy-form.html',
    controller: CopyFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.CopyFormDirective.directive_name = 'grrNewHuntWizardCopyForm';
