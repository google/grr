goog.module('grrUi.stats.reportDescsService');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');


/**
 * Service that serves report plugins descriptors.
 * @export
 * @unrestricted
 */
exports.ReportDescsService = class {
  /**
   * @param {!angular.$q} $q
   * @param {!ApiService} grrApiService
   * @ngInject
   */
  constructor($q, grrApiService) {
    /** @private {!angular.$q} */
    this.q_ = $q;

    /** @private {!ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {*} */
    this.reports_;

    /** @private {*} */
    this.descsByName_;
  }

  /**
   * getDescs is a thin wrapper over the ApiListReports API call that strips the
   * type information, only calls the API once and uses a cached response
   * afterwards.
   *
   * @return {!angular.$q.Promise} A promise that resolves to the list of
   *     ApiReport
   *   objects with the descriptor field filled, as returned by the
   * ApiListReports API call (the response's field response.data.reports, to be
   * precise).
   * @export
   */
  getDescs() {
    const deferred = this.q_.defer();

    if (angular.isDefined(this.reports_)) {
      deferred.resolve(this.reports_);
    } else {
      this.grrApiService_.get('stats/reports').then(function(response) {
        this.reports_ = stripTypeInfo(response['data']['reports']);

        deferred.resolve(this.reports_);
      }.bind(this));
    }

    return deferred.promise;
  }

  /**
   * getDescByName is a convenience wrapper over getDescs that resolves to a
   * single descriptor with the given name.
   *
   * @param {string} name The sought desc's name.
   * @return {!angular.$q.Promise} A promise that resolves to the sought
   *   descriptor if it exists, undefined otherwise.
   * @export
   */
  getDescByName(name) {
    const deferred = this.q_.defer();

    if (angular.isDefined(this.descsByName_)) {
      // Nore that this will resolve to undefined if name is not in the dict.
      deferred.resolve(this.descsByName_[name]);
    } else {
      this.getDescs().then(function(reports) {
        this.descsByName_ = {};
        for (let i = 0; i < reports.length; i++) {
          const desc = reports[i]['desc'];
          this.descsByName_[desc['name']] = desc;
        }

        deferred.resolve(this.descsByName_[name]);
      }.bind(this));
    }

    return deferred.promise;
  }
};
const ReportDescsService = exports.ReportDescsService;

ReportDescsService.service_name = 'grrReportDescsService';
