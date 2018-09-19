goog.module('grrUi.hunt.rapidHuntStatusDirective');
goog.module.declareLegacyNamespace();


/**
 * Helper function to validate FileFinderArgs.path.
 *
 * @param {!Object} path A GlobExpression object.
 * @return {boolean} True if the path has more than one "*" symbols in it. False
 *     otherwise.
 */
const isPathInvalid_ = (path) => {
  return (path['value'].match(/\*/g) || []).length > 1;
};

/**
 * Checks given flowName/flowArgs for rapid-hunting eligibility.
 *
 * @param {string} flowName Name of the flow.
 * @param {!Object} flowArgs Flow arguments object.
 * @return {boolean} True if flowName/flowArgs are rapid-hunting eligible,
 *     false otherwise.
 * @export
 */
exports.isEligible = (flowName, flowArgs) => {
  if (flowName !== 'FileFinder' && flowName !== 'ClientFileFinder') {
    return false;
  }

  const hasInvalidPath = (flowArgs['value']['paths'] || []).find(
      isPathInvalid_);
  if (hasInvalidPath) {
    return false;
  }

  if (flowArgs['value']['action'] !== undefined &&
      flowArgs['value']['action']['value']['action_type'] &&
      flowArgs['value']['action']['value']['action_type']['value'] === 'DOWNLOAD') {
    return false;
  }

  return true;
};
const isEligible = exports.isEligible;

/**
 * Controller for RapidHuntStatusDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const RapidHuntStatusController = function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.enabled = false;

  this.isEligible = false;

  this.grrApiService_.getCached('/config/AdminUI.rapid_hunts_enabled')
      .then((response) => {
        this.enabled = response['data']['value']['value'];

        if (this.enabled) {
          this.scope_.$watch('flowName', this.onFlowChange_.bind(this));
          this.scope_.$watch('flowArgs', this.onFlowChange_.bind(this));
        }
      });
};

/**
 * Callback called every time either flowName or flowArgs binding changes.
 *
 * @private
 */
RapidHuntStatusController.prototype.onFlowChange_ = function() {
  if (angular.isUndefined(this.scope_['flowName']) ||
      angular.isUndefined(this.scope_['flowArgs'])) {
    return;
  }

  this.scope_['isEligible'] = this.isEligible = isEligible(
      this.scope_['flowName'], this.scope_['flowArgs']);
};

/**
 * Directive for displaying rapid hunting eligibility status note.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.RapidHuntStatusDirective = function() {
  return {
    scope: {
      /**
       * In-binding with the name of the hunt flow.
       */
      flowName: '<',
      /**
       * In-binding with hunt flow arguments object.
       */
      flowArgs: '<',
      /**
       * In-binding with the current hunt client rate.
       * Current hunt client rate setting influences presentation (see the
       * template for d
       */
      clientRate: '<',
      /**
       * Out binding that is set to true if flowName/flowArgs make the hunt
       * eligible for rapid hunting.
       */
      isEligible: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/rapid-hunt-status.html',
    controller: RapidHuntStatusController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.RapidHuntStatusDirective.directive_name = 'grrRapidHuntStatus';
