'use strict';

goog.module('grrUi.forms.foremanLabelRuleFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ForemanLabelRuleFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
const ForemanLabelRuleFormController =
    function($scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @private string */
  this.defaultLabel_ = "";

  this.grrReflectionService_.getRDFValueDescriptor(
      'ForemanLabelClientRule').then(function(descriptor) {
    angular.forEach(descriptor['fields'], function(field) {
      if (field['name'] == 'match_mode') {
        this.matchModeMetadata = field;
      }
    }.bind(this));

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
exports.ForemanLabelRuleFormDirective = function() {
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
exports.ForemanLabelRuleFormDirective.directive_name = 'grrFormLabel';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.ForemanLabelRuleFormDirective.semantic_type = 'ForemanLabelClientRule';
