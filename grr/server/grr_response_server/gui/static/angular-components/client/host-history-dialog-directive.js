goog.module('grrUi.client.hostHistoryDialogDirective');

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');
const {TimeService} = goog.require('grrUi.core.timeService');


/**
 * Controller for HostHistoryDialogDirective.
 * @unrestricted
 */
const HostHistoryDialogController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!ApiService} grrApiService
   * @param {!TimeService} grrTimeService
   * @ngInject
   */
  constructor($scope, grrApiService, grrTimeService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!TimeService} grrTimeService */
    this.grrTimeService_ = grrTimeService;

    /** @type {Array<Object>|undefined} */
    this.items;

    /** @type {Object} */
    this.endTime;

    /** @type {Object} */
    this.startTime;

    this.scope_.$watchGroup(
        ['clientId', 'fieldPath'], this.onParamsChange_.bind(this));
  }

  /**
   * Handles changes in huntId binding.
   *
   * @private
   */
  onParamsChange_() {
    const clientId = this.scope_['clientId'];
    const fieldPath = this.scope_['fieldPath'];

    if (angular.isDefined(clientId) && angular.isDefined(fieldPath)) {
      const endTime = this.grrTimeService_.getCurrentTimeMs() * 1000;
      const startTime = endTime - 1000000 * 60 * 60 * 24 * 365;

      this.startTime = {type: 'RDFDatetime', value: startTime};

      this.endTime = {type: 'RDFDatetime', value: endTime};

      this.grrApiService_
          .get(
              '/clients/' + clientId + '/versions',
              {mode: 'DIFF', start: startTime, end: endTime})
          .then(function(response) {
            this.buildItems_(response['data']['items']);
          }.bind(this));
    }
  }

  /**
   * @param {Object} version
   * @param {string} fieldPath
   * @return {Object}
   *
   * @private
   */
  getFieldFromVersion_(version, fieldPath) {
    const components = fieldPath.split('.');
    let curValue = version;
    for (let i = 0; i < components.length; ++i) {
      const component = components[i];
      curValue = curValue['value'][component];
      if (angular.isUndefined(curValue)) {
        break;
      }
    }
    return curValue;
  }

  /**
   * Builds items to display from the server's response.
   *
   * @param {!Array<Object>} versions Versions fetched from the service.

   * @private
   */
  buildItems_(versions) {
    const fieldPath = this.scope_['fieldPath'];

    let prevCompareValue;
    this.items = [];
    angular.forEach(versions, function(version) {
      const versionValue = this.getFieldFromVersion_(version, fieldPath);
      if (angular.isUndefined(versionValue)) {
        return;
      }

      // stripTypeInfo strips not only types, but also "age" properties,
      // which may influence angular.equals() behavior.
      const compareValue = stripTypeInfo(versionValue);
      if (angular.equals(prevCompareValue, compareValue)) {
        return;
      }

      this.items.push([version['value']['age'], versionValue]);
      prevCompareValue = compareValue;
    }.bind(this));

    this.items.reverse();
  }
};



/**
 * Displays a "Client history" dialog.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.HostHistoryDialogDirective = function() {
  return {
    scope: {clientId: '=', fieldPath: '=', close: '&'},
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
exports.HostHistoryDialogDirective.directive_name = 'grrHostHistoryDialog';
