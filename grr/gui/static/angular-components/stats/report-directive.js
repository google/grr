'use strict';

goog.provide('grrUi.stats.reportDirective.ReportController');
goog.provide('grrUi.stats.reportDirective.ReportDirective');

goog.require('grrUi.core.apiService.stripTypeInfo');
goog.require('grrUi.core.utils.upperCaseToTitleCase');

goog.scope(function() {

var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/** @type {number} */
var WEEK_SECONDS = 7*24*60*60;

// A week ago
/** @type {number} */
var DEFAULT_START_TIME_SECS =
    Math.ceil(moment().valueOf() / 1000 - WEEK_SECONDS);

// One week
/** @type {number} */
var DEFAULT_DURATION_SECS = WEEK_SECONDS;

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
  this.typedReportData;

  /** @type {*} */
  this.reportData;

  /** @type {*} */
  this.reportDesc;

  /** @type {number|null} */
  this.startTime = null;

  /** @type {number|null} */
  this.duration = null;

  /** @type {string|null} */
  this.clientLabel = null;

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
  if (angular.isDefined(startTime)) {
    this.startTime = startTime;
  }

  var duration = this.scope_['duration'];
  if (angular.isDefined(duration)) {
    this.duration = duration;
  }

  var clientLabel = this.scope_['clientLabel'];
  if (angular.isDefined(clientLabel)) {
    this.clientLabel = clientLabel;
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

    var startTime = DEFAULT_START_TIME_SECS;
    if (this.startTime !== null) {
      startTime = this.startTime;
    }

    var duration = DEFAULT_DURATION_SECS;
    if (this.duration !== null) {
      duration = this.duration;
    }

    var clientLabel = DEFAULT_CLIENT_LABEL;
    if (this.clientLabel !== null) {
      clientLabel = this.clientLabel;
    }

    var apiUrl = 'stats/reports/' + name;
    var apiParams = {
      start_time: startTime * 1e6,  // conversion to μs
      duration: duration,
      client_label: clientLabel
    };

    this.grrApiService_.get(apiUrl, apiParams).then(function(response) {
      this.typedReportData = response['data']['data'];
      this.reportData = stripTypeInfo(this.typedReportData);
      this.reportDesc = stripTypeInfo(response['data']['desc']);

      if (this.reportDesc['requires_time_range']) {
        this.startTime = startTime;
        this.duration = duration;
      }

      if (this.reportDesc['type'] === 'CLIENT') {
        this.clientLabel = clientLabel;
      }

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
