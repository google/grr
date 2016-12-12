'use strict';

goog.provide('grrUi.user.userNotificationItemDirective.UserNotificationItemController');
goog.provide('grrUi.user.userNotificationItemDirective.UserNotificationItemDirective');
goog.provide('grrUi.user.userNotificationItemDirective.annotateApiNotification');
goog.provide('grrUi.user.userNotificationItemDirective.openReference');
goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');
goog.require('grrUi.core.apiService.encodeUrlPath');
goog.require('grrUi.core.apiService.stripTypeInfo');
goog.require('grrUi.core.utils.getLastPathComponent');
goog.require('grrUi.core.utils.stripAff4Prefix');

goog.scope(function() {

var encodeUrlPath = grrUi.core.apiService.encodeUrlPath;
var getLastPathComponent = grrUi.core.utils.getLastPathComponent;
var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;
var getFileId = grrUi.client.virtualFileSystem.fileViewDirective.getFileId;
var stripAff4Prefix = grrUi.core.utils.stripAff4Prefix;

/**
 * Opens the reference of a notification.
 *
 * @param {Object} notification
 * @param {!angular.$window} angularWindow
 * @return {boolean} Returns true if the location was changed.
 *
 * @export
 */
grrUi.user.userNotificationItemDirective.openReference =
    function(notification, angularWindow) {
  if (!notification['isFileDownload'] && notification['link']) {
    angularWindow.location.href = '#/' + notification['link'];
    return true;
  } else {
    return false;
  }
};
var openReference = grrUi.user.userNotificationItemDirective.openReference;

/**
 * Prepares the notification for displaying.
 *
 * @param {Object} notification
 */
grrUi.user.userNotificationItemDirective.annotateApiNotification =
    function(notification) {
  notification['isPending'] = notification['value']['is_pending']['value'];

  if (angular.isDefined(notification['value']['reference'])) {
    notification['link'] = getLink_(notification);
    notification['refType'] =
        notification['value']['reference']['value']['type']['value'];
  }
};
var annotateApiNotification = grrUi.user.userNotificationItemDirective.annotateApiNotification;

/**
 * Creates a link for the notification.
 *
 * @param {Object} notification The notification.
 * @return {Object<string, string>|string} The URL parameters or the URL
 * path for the given notification.
 *
 * @private
 */
var getLink_ = function(notification) {
  var strippedNotification = stripTypeInfo(notification);
  if (!strippedNotification['reference'] ||
      !strippedNotification['reference']['type']){
    return null;
  }

  var reference = strippedNotification['reference'];
  var referenceType = reference['type'];
  var referenceDetails = reference[referenceType.toLowerCase()];
  var urlParameters = {};

  if (referenceType === 'DISCOVERY') {
    return ['clients',
            stripAff4Prefix(referenceDetails['client_id'])].join('/');
  } else if (referenceType === 'HUNT') {
    var huntId = getLastPathComponent(referenceDetails['hunt_urn']);
    return ['hunts',
            huntId].join('/');
  } else if (referenceType === 'CRON') {
    var cronJobName = getLastPathComponent(referenceDetails['cron_job_urn']);
    return ['crons',
            cronJobName].join('/');
  } else if (referenceType === 'VFS') {
    return ['clients',
            stripAff4Prefix(referenceDetails['client_id']),
            'vfs',
            encodeUrlPath(stripAff4Prefix(referenceDetails['vfs_path']))].join('/');
  } else if (referenceType == 'FLOW') {
    var flowId = referenceDetails['flow_id'];
    return ['clients',
            stripAff4Prefix(referenceDetails['client_id']),
            'flows',
            flowId].join('/');
  } else if (referenceType === 'CLIENT_APPROVAL') {
    var clientId = stripAff4Prefix(referenceDetails['client_id']);
    return ['users',
            referenceDetails['username'],
            'approvals',
            'client',
            clientId,
            referenceDetails['approval_id']].join('/');
  } else if (referenceType === 'HUNT_APPROVAL') {
    return ['users',
            referenceDetails['username'],
            'approvals',
            'hunt',
            referenceDetails['hunt_id'],
            referenceDetails['approval_id']].join('/');
  } else if (referenceType === 'CRON_JOB_APPROVAL') {
    return ['users',
            referenceDetails['username'],
            'approvals',
            'cron-job',
            referenceDetails['cron_job_id'],
            referenceDetails['approval_id']].join('/');
  }

  return null;
};

/**
 * Gets the file id for the full vfs path, which includes aff4:/<client>/.
 *
 * @param {string} vfsPath The full vfs path.
 * @return {string} The file id for the given VFS path.
 * @private
 */
var getFileIdFromFullPath_ = function(vfsPath) {
  var components = vfsPath.split('/').slice(2, -1);
  return getFileId(components.join('/'));
};


/**
 * Controller for UserNotificationItemDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$window} $window
 * @constructor
 * @ngInject
 */
grrUi.user.userNotificationItemDirective.UserNotificationItemController =
  function($scope, $window) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$window} */
  this.window_ = $window;

  this.scope_.$watch('notification', this.onNotificationChanged_.bind(this));
};

var UserNotificationItemController = grrUi.user.userNotificationItemDirective.UserNotificationItemController;


/**
 * Prepares the notification for displaying.
 *
 * @param {Object} notification
 * @private
 */
UserNotificationItemController.prototype.onNotificationChanged_ = function(
    notification) {
  annotateApiNotification(notification);
};

/**
 * Opens the reference of the notification.
 *
 * @export
 */
UserNotificationItemController.prototype.openReference = function() {
  if (openReference(this.scope_['notification'], this.window_)) {
    this.scope_['close']();
  }
};


/**
 * Directive for showing a notification.
 *
 * @return {angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.user.userNotificationItemDirective.UserNotificationItemDirective = function() {
  return {
    scope: {
      notification: '=',
      close: '&'
    },
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
grrUi.user.userNotificationItemDirective.UserNotificationItemDirective.directive_name =
  'grrUserNotificationItem';


});  // goog.scope
