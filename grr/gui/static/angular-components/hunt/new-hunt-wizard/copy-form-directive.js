'use strict';

goog.provide('grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormController');
goog.provide('grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective');

goog.scope(function() {

/**
 * Controller for CopyFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormController =
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

  this.grrReflectionService_.getRDFValueDescriptor('ApiCreateHuntArgs').then(function(descriptor) {
    this.createHuntArgsDescriptor = descriptor;

    this.scope_.$watch('huntUrn', this.onHuntUrnChange_.bind(this));
  }.bind(this));
};
var CopyFormController =
    grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormController;


/**
 * Handles huntUrn attribute changes.
 *
 * @private
 */
CopyFormController.prototype.onHuntUrnChange_ = function() {
  if (angular.isDefined(this.scope_.huntUrn)) {
    var huntUrnComponents = this.scope_.huntUrn.split('/');
    this.huntId = huntUrnComponents[huntUrnComponents.length - 1];

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
};


/**
 * Displays a new hunt wizard form with fields prefilled from another hunt.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective = function() {
  return {
    scope: {
      huntUrn: '=',
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
grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective.directive_name =
    'grrNewHuntWizardCopyForm';

});  // goog.scope
