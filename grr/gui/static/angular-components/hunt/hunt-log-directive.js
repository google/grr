'use strict';

goog.module('grrUi.hunt.huntLogDirective');
goog.module.declareLegacyNamespace();



/** @type {number} */
let AUTO_REFRESH_INTERVAL_MS = 20 * 1000;

/**
 * Sets the delay between automatic refreshes.
 *
 * @param {number} millis Interval value in milliseconds.
 * @export
 */
exports.setAutoRefreshInterval = function(millis) {
  AUTO_REFRESH_INTERVAL_MS = millis;
};


/**
 * Controller for HuntLogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const HuntLogController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntId;

  /** @type {number} */
  this.autoRefreshInterval = AUTO_REFRESH_INTERVAL_MS;

  this.scope_.$watch('huntId', this.onHuntIdChange_.bind(this));
};



/**
 * Handles huntId attribute changes.

 * @param {string} huntId
 * @private
 */
HuntLogController.prototype.onHuntIdChange_ = function(huntId) {
  if (angular.isDefined(huntId)) {
    this.logsUrl = 'hunts/' + huntId + '/log';
  }
};


/**
 * Marks even groups of neighboring records with same client IDs as
 * highlighted.
 * Fills short_urn attribute of every item with a last component of
 * a full item's URN.
 *
 * @param {!Array<Object>} items Array of log items.
 * @return {!Array<Object>} Transformed items.
 * @export
 * @suppress {missingProperties} as we're working with JSON data.
 */
HuntLogController.prototype.transformItems = function(items) {
  var clientId = null;
  var highlighted = false;
  for (var i = 0; i < items.length; ++i) {
    var item = items[i];

    // Highlight rows with a similar client id with the same
    // highlight. Also show the client id only once per group
    // of messages.
    var itemClientId = null;
    if (item.value.client_id !== undefined) {
      itemClientId = item.value.client_id.value;
    }

    if (clientId !== itemClientId) {
      clientId = itemClientId;
      highlighted = !highlighted;
    } else {
      item.value.client_id = null;
    }

    item.highlighted = highlighted;
  }

  return items;
};



/**
 * Directive for displaying log records of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HuntLogDirective = function() {
  return {
    scope: {
      huntId: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-log.html',
    controller: HuntLogController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntLogDirective.directive_name = 'grrHuntLog';
