'use strict';

goog.provide('grrUi.forms.foremanLabelRuleFormDirective');
goog.provide('grrUi.forms.foremanLabelRuleFormDirective.ForemanLabelRuleFormController');
goog.provide('grrUi.forms.foremanLabelRuleFormDirective.ForemanLabelRuleFormDirective');
goog.scope(function() {


/**
 * Controller for ForemanLabelRuleFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.forms.foremanLabelRuleFormDirective.ForemanLabelRuleFormController =
    function($scope, grrReflectionService, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {Array<Object>} */
  this.labelsList = [];

  /** @private string **/
  this.defaultLabel_ = "";

  this.grrReflectionService_.getRDFValueDescriptor(
      'ForemanLabelClientRule').then(function(descriptor) {
    angular.forEach(descriptor['fields'], function(field) {
      if (field['name'] == 'match_mode') {
        this.matchModeMetadata = field;
      }
    }.bind(this));

    return this.grrApiService_.get('/clients/labels');
  }.bind(this)).then(function(response) {

    this.labelsList = response['data']['items'];
    if (this.labelsList.length > 0) {
      this.defaultLabel_ = this.labelsList[0]['value']['name']['value'];
    }

    this.scope_.$watch('value.value', function(value) {
      if (angular.isDefined(value)) {
        if (angular.isUndefined(value['match_mode'])) {
          value['match_mode'] = angular.copy(this.matchModeMetadata['default']);
        }

        if (angular.isUndefined(value['label_names'])) {
          value['label_names'] = [];
        }
        if (value['label_names'].length == 0) {
          this.addLabel();
        }
      }
    }.bind(this));
  }.bind(this));
};
var ForemanLabelRuleFormController =
    grrUi.forms.foremanLabelRuleFormDirective.ForemanLabelRuleFormController;


/**
 * Adds a new label to the list.
 *
 * @export
 */
ForemanLabelRuleFormController.prototype.addLabel = function() {
  this.scope_['value']['value']['label_names'].push({
    type: 'unicode',
    value: this.defaultLabel_
  });
};

/**
 * Removes label with a given index from the list.
 *
 * @param {number} index Index of the label to be removed.
 * @export
 */
ForemanLabelRuleFormController.prototype.removeLabel = function(index) {
  this.scope_['value']['value']['label_names'].splice(index, 1);
};

/**
 * ForemanLabelRuleFormDirective renders a ForemanLabelClientRule.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.foremanLabelRuleFormDirective.ForemanLabelRuleFormDirective =
    function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '='
    },
    templateUrl:
        '/static/angular-components/forms/foreman-label-rule-form.html',
    controller: ForemanLabelRuleFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.foremanLabelRuleFormDirective.ForemanLabelRuleFormDirective
    .directive_name = 'grrFormLabel';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.foremanLabelRuleFormDirective.ForemanLabelRuleFormDirective
    .semantic_type = 'ForemanLabelClientRule';

});  // goog.scope
