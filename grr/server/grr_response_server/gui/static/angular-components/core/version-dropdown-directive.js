'use strict';

goog.module('grrUi.core.versionDropdownDirective');
goog.module.declareLegacyNamespace();



var REFRESH_VERSIONS_EVENT = "RefreshVersionsEvent";


/**
 * Controller for VersionDropdownDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const VersionDropdownController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array} */
  this.versions;

  /** @type {?string} */
  this.version;

  /** @private {number} */
  this.requestCounter_ = 0;

  /** @private {boolean} */
  this.updateInProgress_;

  // When either a URL or a current version changes, refresh the versions list.
  this.scope_.$watch('url', this.fetchVersions_.bind(this));

  this.scope_.$watch('version', this.onVersionBindingChange_.bind(this));

  this.scope_.$watch('controller.version',
                     this.onControllerVersionChange_.bind(this));

  this.scope_.$on(REFRESH_VERSIONS_EVENT, this.fetchVersions_.bind(this));
};



/**
 * Handles changes in the 'version' binding. Assigns a default 'HEAD' value
 * if no version is selected or ensures that selected version is in the list.
 *
 * @param {?string} newValue
 * @private
 */
VersionDropdownController.prototype.onVersionBindingChange_ = function(
    newValue) {
  if (angular.isUndefined(newValue) && this.version === 'HEAD') {
    return;
  }

  if (angular.isDefined(this.versions)) {
    for (var i = 0; i < this.versions.length; ++i) {
      if (newValue === this.versions[i]['value']) {
        this.version = this.scope_['version'].toString();
        return;
      }
    }
  }

  this.syncSelectedVersion_();
};


/**
 * Ensures that a version specified in the directive's 'version' binding
 * is present in the versions list and that controller's 'version' binding
 * has a correct corresponding value.
 *
 * @private
 */
VersionDropdownController.prototype.syncSelectedVersion_ = function() {
  if (angular.isUndefined(this.versions) || this.versions.length === 0) {
    return;
  }

  // If version is specified, ensure it's present in the list.
  if (this.scope_['version']) {
    this.versions.push({
      value: this.scope_['version'],
      type: 'RDFDatetime'
    });

    // Sort the array by value in the descending order.
    this.versions.sort(function(v1, v2) {
      if (v1['value'] < v2['value']) {
        return 1;
      } else if (v1['value'] == v2['value']) {
        return 0;
      } else {
        return -1;
      }
    }.bind(this));
    // Remove duplicates from a sorted array.
    this.versions = this.versions.filter(function(value, index, arr) {
      if (index == 0) {
        return true;
      } else {
        return value['value'] != arr[index - 1]['value'];
      }
    }.bind(this));

    this.version = this.scope_['version'].toString();
  } else {
    this.version = 'HEAD';
  }
};

/**
 * Fetches the versions.
 *
 * @private
 */
VersionDropdownController.prototype.fetchVersions_ = function() {
  var url = this.scope_['url'];

  if (angular.isDefined(url)) {
    this.updateInProgress_ = true;
    this.requestCounter_ += 1;
    var curCounter = this.requestCounter_;

    this.grrApiService_.get(url)
        .then(function(response) {
          // Make sure that the response we got corresponds to the latest
          // request we sent.
          if (curCounter === this.requestCounter_) {
            this.onVersionsFetched_(response);
            this.updateInProgress_ = false;
          }
        }.bind(this));
  }
};


/**
 * Processes fetched versions.
 *
 * @param {!Object} response
 * @private
 */
VersionDropdownController.prototype.onVersionsFetched_ = function(response) {
  var responseField = this.scope_['responseField'] || 'times';

  this.versions = response['data'][responseField];

  // If no versions were fetched from the server, do nothing and
  // do not change the model (by changing this.version).
  if (!this.versions.length) {
    return;
  }

  this.syncSelectedVersion_();
};

/**
 * Handles changes to the controller version.
 *
 * @private
 */
VersionDropdownController.prototype.onControllerVersionChange_ = function() {
  if (angular.isUndefined(this.version)) {
    return;
  }

  // Since we cannot use ng-options, we need to convert the string selection to a number.
  if (this.version == 'HEAD') {
    this.scope_['version'] = undefined;
  } else {
    this.scope_['version'] = parseInt(this.version, 10);
  }
};

/**
 * Checks whether a version is the currently selected one.
 *
 * @param {number} value The number representation of a version.
 * @return {boolean} True if the latest item is selected, false otherwise.
 * @export
 */
VersionDropdownController.prototype.isSelected = function(value) {
  if (value == 'HEAD') {
    return this.version == value;
  } else {
    return parseInt(this.version, 10) == value;
  }
};

/**
 * Checks whether the latest item is selected or not.
 *
 * @return {boolean} True if the latest item is selected, false otherwise.
 * @export
 */
VersionDropdownController.prototype.isLatestSelected = function() {
  if (this.updateInProgress_){
    return true; // As we do not know about the elements that will be returned,
                 // we assume we have the latest version.
  }

  if (this.version == 'HEAD') {
    return true;
  }

  return !this.versions || this.versions.length === 0 || !this.scope_['version']
      || this.version === this.versions[0].value.toString();
};

/**
 * VersionDropdownDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.VersionDropdownDirective = function() {
  return {
    restrict: 'E',
    scope: {
      url: '=',
      version: '=',
      responseField: '@'
    },
    templateUrl: '/static/angular-components/core/version-dropdown.html',
    controller: VersionDropdownController,
    controllerAs: 'controller'
  };
};

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.VersionDropdownDirective.directive_name = 'grrVersionDropdown';

/**
 * "Refresh versions" event name.
 * @const
 */
exports.VersionDropdownDirective.REFRESH_VERSIONS_EVENT =
    REFRESH_VERSIONS_EVENT;
