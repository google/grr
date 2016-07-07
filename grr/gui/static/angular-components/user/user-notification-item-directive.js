'use strict';

goog.provide('grrUi.user.userNotificationItemDirective.UserNotificationItemController');
goog.provide('grrUi.user.userNotificationItemDirective.UserNotificationItemDirective');
goog.provide('grrUi.user.userNotificationItemDirective.annotateApiNotification');
goog.provide('grrUi.user.userNotificationItemDirective.openReference');
goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');
goog.require('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {

var module = grrUi.user.userNotificationItemDirective;
var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;
var getFileId = grrUi.client.virtualFileSystem.fileViewDirective.getFileId;

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
    angularWindow.location.href = '#' + notification['link'];
    return true;
  } else {
    return false;
  }
};
var openReference = module.openReference;

/**
 * Prepares the notification for displaying.
 *
 * @param {Object} notification
 */
grrUi.user.userNotificationItemDirective.annotateApiNotification =
    function(notification) {
  var urlParams = getUrlParameters_(notification);
  notification['isPending'] = notification['value']['is_pending']['value'];
  if (urlParams) {
    notification['link'] = $.param(urlParams);
    notification['isFileDownload'] = urlParams['main'] === 'DownloadFile';
    notification['refType'] =
        notification['value']['reference']['value']['type']['value'];
    if (notification['isFileDownload']) {
      notification['path'] = urlParams['aff4_path'];
    }

    if (notification['refType'] == 'VFS') {
      var vfsPath =  notification['value']['reference']['value'][
        'vfs']['value']['vfs_path']['value'];
      if (vfsPath.indexOf('/MACTimes/') != -1) {
        notification['legacyMacTimes'] = true;
      } else if (vfsPath.indexOf('/fs/os/') == -1 &&
          vfsPath.indexOf('/fs/tsk/') == -1 &&
          vfsPath.indexOf('/registry/') == -1) {
        notification['legacyVfsPath'] = true;
      }
    }
  }
};
var annotateApiNotification = module.annotateApiNotification;

/**
 * Creates a link for the notification.
 *
 * @param {Object} notification The notification.
 * @return {Object<string, string>} The URL parameters for the given
 *                                  notification.
 * @private
 */
var getUrlParameters_ = function(notification) {
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
      urlParameters['c'] = referenceDetails['client_id'];
      urlParameters['main'] = 'HostInformation';
  } else if (referenceType === 'FILE_DOWNLOAD_READY') {
      urlParameters['aff4_path'] = referenceDetails['path']
      urlParameters["main"] = "DownloadFile";
  } else if (referenceType === 'HUNT') {
      urlParameters['hunt_id'] = referenceDetails['hunt_urn'];
      urlParameters['main'] = 'ManageHunts';
  } else if (referenceType === 'CRON') {
      urlParameters['cron_job_urn'] = referenceDetails['cron_job_urn'];
      urlParameters['main'] = 'ManageCron';
  } else if (referenceType === 'FLOW') {
      urlParameters['flow'] = referenceDetails['flow_urn'];
      urlParameters['c'] = referenceDetails['client_id'];
      urlParameters['main'] = 'ManageFlows';
  } else if (referenceType === 'VFS') {
      urlParameters['c'] = referenceDetails['client_id'];
      urlParameters['aff4_path'] = referenceDetails['vfs_path'];
      urlParameters['t'] = getFileIdFromFullPath_(referenceDetails['vfs_path']);
      urlParameters['main'] = 'VirtualFileSystemView';
  } else if (referenceType === 'FLOW_STATUS') {
      urlParameters['flow'] = referenceDetails['flow_urn'];
      urlParameters['c'] = referenceDetails['client_id'];
      urlParameters['main'] = 'ManageFlows';
  } else if (referenceType === 'GRANT_ACCESS') {
      urlParameters['acl'] = referenceDetails['acl'];
      urlParameters['main'] = 'GrantAccess';
  }
  return urlParameters;
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
module.UserNotificationItemController =
  function($scope, $window) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$window} */
  this.window_ = $window;

  this.scope_.$watch('notification', this.onNotificationChanged_.bind(this));
};

var UserNotificationItemController = module.UserNotificationItemController;


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
 * @constructor
 * @ngInject
 * @export
 */
module.UserNotificationItemDirective = function() {
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
module.UserNotificationItemDirective.directive_name =
  'grrUserNotificationItem';


});  // goog.scope
