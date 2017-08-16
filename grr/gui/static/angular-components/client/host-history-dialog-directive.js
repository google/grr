'use strict';

goog.provide('grrUi.client.hostHistoryDialogDirective.HostHistoryDialogController');
goog.provide('grrUi.client.hostHistoryDialogDirective.HostHistoryDialogDirective');
goog.require('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {

var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/**
 * Controller for HostHistoryDialogDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.core.timeService.TimeService} grrTimeService
 * @ngInject
 */
grrUi.client.hostHistoryDialogDirective.HostHistoryDialogController =
    function($scope, grrApiService, grrTimeService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.core.timeService.TimeService} grrTimeService */
  this.grrTimeService_ = grrTimeService;

  /** @type {Array<Object>|undefined} */
  this.items;

  /** @type {Object} */
  this.endTime;

  /** @type {Object} */
  this.startTime;

  this.scope_.$watchGroup(['clientId', 'fieldPath'], this.onParamsChange_.bind(this));
};

var HostHistoryDialogController =
    grrUi.client.hostHistoryDialogDirective.HostHistoryDialogController;


/**
 * Handles changes in huntId binding.
 *
 * @private
 */
HostHistoryDialogController.prototype.onParamsChange_ = function() {
  var clientId = this.scope_['clientId'];
  var fieldPath = this.scope_['fieldPath'];

  if (angular.isDefined(clientId) && angular.isDefined(fieldPath)) {
    var endTime = this.grrTimeService_.getCurrentTimeMs() * 1000;
    var startTime = endTime - 1000000 * 60 * 60 * 24 * 365;

    this.startTime = {
      type: 'RDFDatetime',
      value: startTime
    };

    this.endTime = {
      type: 'RDFDatetime',
      value: endTime
    };

    this.grrApiService_.get('/clients/' + clientId + '/versions', {
      mode: 'DIFF',
      start: startTime,
      end: endTime
    }).then(function(response) {
      this.buildItems_(response['data']['items']);
    }.bind(this));
  }
};

HostHistoryDialogController.prototype.getFieldFromVersion_ = function(
    version, fieldPath) {
  var components = fieldPath.split(".");
  var curValue = version;
  for (var i = 0; i < components.length; ++i) {
    var component = components[i];
    curValue = curValue['value'][component];
    if (angular.isUndefined(curValue)) {
      break;
    }
  }
  return curValue;
};


/**
 * Builds items to display from the server's response.
 *
 * @param {!Array<Object>} versions Versions fetched from the service.

 * @private
 */
HostHistoryDialogController.prototype.buildItems_ = function(versions) {
  var fieldPath = this.scope_['fieldPath'];

  var prevCompareValue;
  this.items = [];
  angular.forEach(versions, function(version) {
    var versionValue = this.getFieldFromVersion_(version, fieldPath);
    if (angular.isUndefined(versionValue)) {
      return;
    }

    // stripTypeInfo strips not only types, but also "age" properties,
    // which may influence angular.equals() behavior.
    var compareValue = stripTypeInfo(versionValue);
    if (angular.equals(prevCompareValue, compareValue)) {
      return;
    }

    this.items.push([version['value']['age'], versionValue]);
    prevCompareValue = compareValue;
  }.bind(this));

  this.items.reverse();
};

/**
 * Displays a "Client history" dialog.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.hostHistoryDialogDirective.HostHistoryDialogDirective = function() {
  return {
    scope: {
      clientId: '=',
      fieldPath: '=',
      close: '&'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/client/host-history-dialog.html',
    controller: HostHistoryDialogController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.client.hostHistoryDialogDirective.HostHistoryDialogDirective.directive_name =
    'grrHostHistoryDialog';

});  // goog.scope
