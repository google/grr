goog.module('grrUi.stats.reportDirective');

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');
const {ReflectionService} = goog.require('grrUi.core.reflectionService');
const {ReportDescsService} = goog.require('grrUi.stats.reportDescsService');
const {TimeService} = goog.require('grrUi.core.timeService');
const {upperCaseToTitleCase} = goog.require('grrUi.core.utils');



/** @type {number} */
const WEEK_SECONDS = 7 * 24 * 60 * 60;

// A week ago
/** @type {number} */
const DEFAULT_START_TIME_SECS =
    Math.ceil(moment().valueOf() / 1000 - WEEK_SECONDS);

// One week
/** @type {number} */
const DEFAULT_DURATION_SECS = WEEK_SECONDS;

/** @type {string} */
const DEFAULT_CLIENT_LABEL = '';

/**
 * Controller for ReportDirective.
 * @unrestricted
 */
const ReportController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!ApiService} grrApiService
   * @param {!ReflectionService} grrReflectionService
   * @param {!TimeService} grrTimeService
   * @param {!ReportDescsService} grrReportDescsService
   * @ngInject
   */
  constructor(
      $scope, grrApiService, grrReflectionService, grrTimeService,
      grrReportDescsService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!ReflectionService} */
    this.grrReflectionService_ = grrReflectionService;

    /** @private {!TimeService} */
    this.grrTimeService_ = grrTimeService;

    /** @private {!ReportDescsService} */
    this.grrReportDescsService_ = grrReportDescsService;

    /**
     * @type {string}
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

    /** @private {number} */
    this.latestFetchTime_ = 0;

    this.scope_.$watch('name', function(name) {
      this.grrReportDescsService_.getDescByName(name).then(function(desc) {
        // This if is triggered also when name is undefined.
        if (angular.isUndefined(desc)) {
          return;
        }

        this.reportDesc = desc;

        this.titleCasedType = upperCaseToTitleCase(this.reportDesc['type']);

        this.onParamsChange_();
      }.bind(this));
    }.bind(this));

    this.scope_.$watchGroup(
        ['startTime', 'duration', 'clientLabel'],
        this.onParamsChange_.bind(this));
  }

  /**
   * Handles changes to the scope parameters.
   *
   * @private
   */
  onParamsChange_() {
    const startTime = this.scope_['startTime'];
    if (angular.isDefined(startTime)) {
      this.startTime = startTime;
    }

    const duration = this.scope_['duration'];
    if (angular.isDefined(duration)) {
      this.duration = duration;
    }

    const clientLabel = this.scope_['clientLabel'];
    if (angular.isDefined(clientLabel)) {
      this.clientLabel = clientLabel;
    }

    this.fetchData_();
  }

  /**
   * Handles "Show report" button clicks. Refreshes the report.
   */
  refreshReport() {
    // If the values are different than before, this triggers onParamsChange_
    // which triggers fetchData_.
    this.scope_['startTime'] = this.startTime;
    this.scope_['duration'] = this.duration;
    this.scope_['clientLabel'] = this.clientLabel;
  }

  /**
   * Fetches data from the api call.
   *
   * @private
   */
  fetchData_() {
    if (angular.isUndefined(this.reportDesc)) {
      return;
    }

    const name = this.reportDesc['name'];
    // `!name' handles all falsey values, including '' and undefined.
    if (!name) {
      return;
    }

    this.state = 'LOADING';

    let startTime = DEFAULT_START_TIME_SECS;
    if (this.startTime !== null) {
      startTime = this.startTime;
    }

    let duration = DEFAULT_DURATION_SECS;
    if (this.duration !== null) {
      duration = this.duration;
    }

    let clientLabel = DEFAULT_CLIENT_LABEL;
    if (this.clientLabel !== null) {
      clientLabel = this.clientLabel;
    }

    const apiUrl = 'stats/reports/' + name;
    const apiParams = {
      start_time: startTime * 1e6,  // conversion to μs
      duration: duration,
      client_label: clientLabel
    };

    if (this.reportDesc['requires_time_range']) {
      this.startTime = startTime;
      this.duration = duration;
    }

    if (this.reportDesc['type'] === 'CLIENT') {
      this.clientLabel = clientLabel;
    }

    const fetchTime = this.grrTimeService_.getCurrentTimeMs();
    this.latestFetchTime_ = fetchTime;
    this.grrApiService_.get(apiUrl, apiParams).then(function(response) {
      if (fetchTime !== this.latestFetchTime_) {
        return;
      }

      this.typedReportData = response['data']['data'];
      this.reportData = stripTypeInfo(this.typedReportData);

      this.state = 'LOADED';
    }.bind(this));
  }
};



/**
 * ReportDirective definition.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.ReportDirective = function() {
  return {
    scope: {name: '=?', startTime: '=?', duration: '=?', clientLabel: '=?'},
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
exports.ReportDirective.directive_name = 'grrReport';
