'use strict';

goog.provide('grrUi.stats.reportDirective.ReportController');
goog.provide('grrUi.stats.reportDirective.ReportDirective');

goog.require('grrUi.core.apiService.stripTypeInfo');
goog.require('grrUi.core.utils.upperCaseToTitleCase');

goog.scope(function() {

var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/** @type {number} */
var MONTH_SECONDS = 30*24*60*60;

// A month ago
/** @type {number} */
var DEFAULT_START_TIME = (moment().valueOf() - MONTH_SECONDS * 1000) * 1000;

// One month
/** @type {number} */
var DEFAULT_DURATION = MONTH_SECONDS;

/** @type {string} */
var DEFAULT_CLIENT_LABEL = '';

/**
 * Controller for ReportDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.stats.reportDirective.ReportController = function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string}
   * This is intended to be an enum with the following possible values:
   * 'INITIAL' -- Select a report
   * 'LOADING' -- Loading...
   * 'LOADED' -- Selectors and a chart
   */
  this.state = 'INITIAL';

  /** @type {string} */
  this.titleCasedType;

  /** @type {*} */
  this.reportData;

  /** @type {*} */
  this.reportDesc;

  this.scope_.$watch('name', this.onNameChange_.bind(this));
};
var ReportController =
    grrUi.stats.reportDirective.ReportController;


/**
 * Handles changes to the name scope parameter.
 *
 * @private
 */
ReportController.prototype.onNameChange_ = function(name) {
  if (name) {
    this.fetchData_();
  }
};

/**
 * Fetches data from the api call.
 *
 * @private
 */
ReportController.prototype.fetchData_ = function() {
  var name = this.scope_['name'];

  if (name) {
    this.state = 'LOADING';

    var apiUrl = 'stats/reports/' + name;
    var apiParams = {
      //TODO(user): Handle non-default timeranges and labels.
      start_time: DEFAULT_START_TIME,
      duration: DEFAULT_DURATION,
      client_label: DEFAULT_CLIENT_LABEL
    };

    this.grrApiService_.get(apiUrl, apiParams).then(function(response) {
      this.reportData = stripTypeInfo(response['data']['data']);
      this.reportDesc = stripTypeInfo(response['data']['desc']);

      this.titleCasedType =
          grrUi.core.utils.upperCaseToTitleCase(this.reportDesc['type']);

      this.state = 'LOADED';
    }.bind(this));
  }
};

/**
 * ReportDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.stats.reportDirective.ReportDirective = function() {
  return {
    scope: {
      name: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/report.html',
    controller: ReportController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.stats.reportDirective.ReportDirective.directive_name =
    'grrReport';

});  // goog.scope
