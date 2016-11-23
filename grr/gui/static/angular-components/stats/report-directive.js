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
var DEFAULT_START_TIME_SECS =
    Math.ceil(moment().valueOf() / 1000 - MONTH_SECONDS);

// One month
/** @type {number} */
var DEFAULT_DURATION_SECS = MONTH_SECONDS;

/** @type {string} */
var DEFAULT_CLIENT_LABEL = '';

/**
 * Controller for ReportDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
grrUi.stats.reportDirective.ReportController =
    function($scope, grrApiService, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

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

  /** @type {number} */
  this.startTime = DEFAULT_START_TIME_SECS;

  /** @type {number} */
  this.duration = DEFAULT_DURATION_SECS;

  /** @type {string} */
  this.clientLabel = DEFAULT_CLIENT_LABEL;

  this.scope_.$watchGroup(['name', 'startTime', 'duration', 'clientLabel'],
                          this.onParamsChange_.bind(this));
};
var ReportController =
    grrUi.stats.reportDirective.ReportController;


/**
 * Handles changes to the scope parameters.
 *
 * @private
 */
ReportController.prototype.onParamsChange_ = function() {
  var startTime = this.scope_['startTime'];
  if (startTime) {
    this.startTime = startTime;
  }
  if (startTime === null) {
    this.startTime = DEFAULT_START_TIME_SECS;
  }

  var duration = this.scope_['duration'];
  if (duration) {
    this.duration = duration;
  }
  if (duration === null) {
    this.duration = DEFAULT_DURATION_SECS;
  }

  var clientLabel = this.scope_['clientLabel'];
  if (clientLabel) {
    this.clientLabel = clientLabel;
  }
  if (clientLabel === null) {
    this.clientLabel = DEFAULT_CLIENT_LABEL;
  }

  if (this.scope_['name']) {
    this.fetchData_();
  }
};

/**
 * Handles "Show report" button clicks. Refreshes the report.
 */
ReportController.prototype.refreshReport = function() {
  // If the values are different than before, this triggers onParamsChange_
  // which triggers fetchData_.
  this.scope_['startTime'] = this.startTime;
  this.scope_['duration'] = this.duration;
  this.scope_['clientLabel'] = this.clientLabel;
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
      start_time: this.startTime,
      duration: this.duration * 1e6,  // conversion to μs
      client_label: this.clientLabel
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
      name: '=?',
      startTime: '=?',
      duration: '=?',
      clientLabel: '=?'
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
