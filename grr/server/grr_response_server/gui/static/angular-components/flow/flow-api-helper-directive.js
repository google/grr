goog.module('grrUi.flow.flowApiHelperDirective');
goog.module.declareLegacyNamespace();

const apiHelperService = goog.requireType('grrUi.docs.apiHelperService');
const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Controller for FlowApiHelperDirective.
 * @unrestricted
 */
const FlowApiHelperController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @param {!apiHelperService.ApiHelperService} grrApiHelperService
   * @ngInject
   */
  constructor($scope, grrApiService, grrApiHelperService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!apiHelperService.ApiHelperService} */
    this.grrApiHelperService_ = grrApiHelperService;

    /** @type {string} */
    this.clientId;

    /** @export {Object} */
    this.result;

    this.scope_.$watchGroup(
        ['flowId', 'apiBasePath'], this.onFlowIdOrBasePathChange_.bind(this));
  }

  /**
   * Handles directive's arguments changes.
   *
   * @param {Array<string>} newValues
   * @private
   */
  onFlowIdOrBasePathChange_(newValues) {
    this.flow = null;
    this.result = null;

    if (newValues.every(angular.isDefined)) {
      var flowUrl = this.scope_['apiBasePath'] + '/' + this.scope_['flowId'];
      this.grrApiService_.getV2(flowUrl).then(function(response) {
        var flow = {
          args: response.data['args'],
          name: response.data['name'],
        };
        if (response.data['runnerArgs'] &&
            response.data['runnerArgs']['outputPlugins']) {
          flow['runnerArgs'] = {
            outputPlugins: response.data['runnerArgs']['outputPlugins']
          };
        }

        var createFlow = {flow: flow};
        this.grrApiHelperService_.buildStartFlow(this.clientId, createFlow)
            .then(function(result) {
              this.result = result;
            }.bind(this));
      }.bind(this));
    }
  }
};



/**
 * Displays a new hunt wizard form with fields prefilled from another hunt.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.FlowApiHelperDirective = function() {
  return {
    scope: {flowId: '=', apiBasePath: '='},
    require: '?^grrClientContext',
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-api-helper.html',
    controller: FlowApiHelperController,
    controllerAs: 'controller',
    link: function(scope, element, attrs, grrClientContextCtrl) {
      if (grrClientContextCtrl) {
        scope['controller'].clientId = grrClientContextCtrl.clientId;
      }
    }
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.FlowApiHelperDirective.directive_name = 'grrFlowApiHelper';
