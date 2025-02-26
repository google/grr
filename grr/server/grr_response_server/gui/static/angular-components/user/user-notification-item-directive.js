goog.module('grrUi.user.userNotificationItemDirective');
goog.module.declareLegacyNamespace();

const {encodeUrlPath, stripTypeInfo} = goog.require('grrUi.core.apiService');
const {stripAff4Prefix} = goog.require('grrUi.core.utils');


/**
 * Opens the reference of a notification.
 *
 * @param {Object} notification
 * @param {!angular.$location} $location
 * @return {boolean} Returns true if the location was changed.
 *
 * @export
 */
exports.openReference = function(notification, $location) {
  if (!notification['isFileDownload'] && notification['link']) {
    $location.path(notification['link']);
    return true;
  } else {
    return false;
  }
};
const openReference = exports.openReference;

/**
 * Prepares the notification for displaying.
 *
 * @param {Object} notification
 */
exports.annotateApiNotification = function(notification) {
  notification['isPending'] = notification['value']['is_pending']['value'];

  if (angular.isDefined(notification['value']['reference'])) {
    notification['link'] = getLink_(notification);
    notification['refType'] =
        notification['value']['reference']['value']['type']['value'];
  }
};
const annotateApiNotification = exports.annotateApiNotification;

/**
 * Creates a link for the notification.
 *
 * @param {Object} notification The notification.
 * @return {Object<string, string>|string} The URL parameters or the URL
 * path for the given notification.
 *
 * @private
 */
const getLink_ = function(notification) {
  const strippedNotification = stripTypeInfo(notification);
  if (!strippedNotification['reference'] ||
      !strippedNotification['reference']['type']) {
    return null;
  }

  const reference = strippedNotification['reference'];
  const referenceType = reference['type'];
  const referenceDetails = reference[referenceType.toLowerCase()];
  const urlParameters = {};

  if (referenceType === 'CLIENT') {
    return ['clients', stripAff4Prefix(referenceDetails['client_id'])].join(
        '/');
  } else if (referenceType === 'HUNT') {
    const huntId = referenceDetails['hunt_id'];
    return ['hunts', huntId].join('/');
  } else if (referenceType === 'CRON') {
    const cronJobName = referenceDetails['cron_job_id'];
    return ['crons', cronJobName].join('/');
  } else if (referenceType === 'VFS') {
    return [
      'clients', stripAff4Prefix(referenceDetails['client_id']), 'vfs',
      encodeUrlPath(stripAff4Prefix(referenceDetails['vfs_path']))
    ].join('/');
  } else if (referenceType == 'FLOW') {
    const flowId = referenceDetails['flow_id'];
    return [
      'clients', stripAff4Prefix(referenceDetails['client_id']), 'flows', flowId
    ].join('/');
  } else if (referenceType === 'CLIENT_APPROVAL') {
    const clientId = stripAff4Prefix(referenceDetails['client_id']);
    return [
      'users', referenceDetails['username'], 'approvals', 'client', clientId,
      referenceDetails['approval_id']
    ].join('/');
  } else if (referenceType === 'HUNT_APPROVAL') {
    return [
      'users', referenceDetails['username'], 'approvals', 'hunt',
      referenceDetails['hunt_id'], referenceDetails['approval_id']
    ].join('/');
  } else if (referenceType === 'CRON_JOB_APPROVAL') {
    return [
      'users', referenceDetails['username'], 'approvals', 'cron-job',
      referenceDetails['cron_job_id'], referenceDetails['approval_id']
    ].join('/');
  }

  return null;
};


/**
 * Controller for UserNotificationItemDirective.
 * @unrestricted
 */
const UserNotificationItemController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.$location} $location
   * @ngInject
   */
  constructor($scope, $location) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.$location} */
    this.location_ = $location;

    this.scope_.$watch('notification', this.onNotificationChanged_.bind(this));
  }

  /**
   * Prepares the notification for displaying.
   *
   * @param {Object} notification
   * @private
   */
  onNotificationChanged_(notification) {
    annotateApiNotification(notification);
  }

  /**
   * Opens the reference of the notification.
   *
   * @export
   */
  openReference() {
    if (openReference(this.scope_['notification'], this.location_)) {
      this.scope_['close']();
    }
  }
};



/**
 * Directive for showing a notification.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.UserNotificationItemDirective = function() {
  return {
    scope: {notification: '=', close: '&'},
    restrict: 'E',
    templateUrl: '/static/angular-components/user/user-notification-item.html',
    controller: UserNotificationItemController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.UserNotificationItemDirective.directive_name =
    'grrUserNotificationItem';
