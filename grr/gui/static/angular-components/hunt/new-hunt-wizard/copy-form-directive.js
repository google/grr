'use strict';

goog.provide('grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormController');
goog.provide('grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective');

goog.scope(function() {

/**
 * Controller for CopyFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Object} */
  this.genericHuntArgs;

  /** @type {Object} */
  this.huntRunnerArgs;

  this.scope_.$watch('huntUrn', this.onHuntUrnChange_.bind(this));
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

  this.genericHuntArgs = angular.copy(hunt['hunt_args']);
  this.huntRunnerArgs = angular.copy(hunt['hunt_runner_args']);

  if (angular.isDefined(this.huntRunnerArgs['value']['description'])) {
    this.huntRunnerArgs['value']['description']['value'] += ' (copy)';
  }
};


/**
 * Called when 'genericHuntArgs' binding changes.
 *
 * @param {Object} newValue New binding value.
 * @private
 */
CopyFormController.prototype.onHuntResponse_ = function(newValue) {
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
