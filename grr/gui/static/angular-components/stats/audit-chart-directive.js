'use strict';

goog.module('grrUi.stats.auditChartDirective');
goog.module.declareLegacyNamespace();

const {stripTypeInfo} = goog.require('grrUi.core.apiService');
const {upperCaseToTitleCase} = goog.require('grrUi.core.utils');



/**
 * Controller for AuditChartDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @constructor
 * @ngInject
 */
const AuditChartController = function(
    $scope, $element) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @type {Array<string>|undefined} */
  this.auditUsedFields;

  /** @type {Array<string>|undefined} */
  this.auditTitleCaseUsedFields;

  /** @type {Array<Array<string>>|undefined} */
  this.typedAuditRows;

  /** @type {string} */
  this.errorMsg = '';

  this.scope_.$watch('typedData', function(typedData) {
    if (angular.isDefined(typedData) &&
        angular.isDefined(typedData['value'])) {
      this.initAuditChart_(typedData['value']['audit_chart']);
    }
  }.bind(this));
};


/**
 * Initializes an audit chart.
 *
 * @param {Object} typedAuditChartData The data to be displayed, with type
 *                                     annotations.
 * @private
 */
AuditChartController.prototype.initAuditChart_ = function(typedAuditChartData) {
  var auditChartData = stripTypeInfo(typedAuditChartData);

  this.auditUsedFields = undefined;
  this.auditTitleCaseUsedFields = undefined;
  this.typedAuditRows = undefined;

  if (angular.isUndefined(auditChartData['rows']) ||
      auditChartData['rows'].length == 0 ||
      angular.isUndefined(auditChartData['used_fields']) ||
      auditChartData['used_fields'].length == 0) {
    this.errorMsg = 'No data to display.';
    return;
  }

  this.auditUsedFields = auditChartData['used_fields'];
  this.auditTitleCaseUsedFields =
      auditChartData['used_fields'].map(upperCaseToTitleCase);
  this.typedAuditRows = typedAuditChartData['value']['rows'];
};

/**
 * AuditChartDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.AuditChartDirective = function() {
  return {
    scope: {
      typedData: "="
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/audit-chart.html',
    controller: AuditChartController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.AuditChartDirective.directive_name = 'grrAuditChart';
