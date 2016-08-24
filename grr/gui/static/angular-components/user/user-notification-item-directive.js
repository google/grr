'use strict';

goog.provide('grrUi.user.userNotificationItemDirective.UserNotificationItemController');
goog.provide('grrUi.user.userNotificationItemDirective.UserNotificationItemDirective');
goog.provide('grrUi.user.userNotificationItemDirective.annotateApiNotification');
goog.provide('grrUi.user.userNotificationItemDirective.openReference');
goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');
goog.require('grrUi.core.apiService.stripTypeInfo');
goog.require('grrUi.core.fileDownloadUtils.vfsRoots');
goog.require('grrUi.core.utils.stripAff4Prefix');

goog.scope(function() {

var module = grrUi.user.userNotificationItemDirective;
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
    if (angular.isObject(urlParams)) {
      notification['link'] = $.param(/** @type {Object} */ (urlParams));
    } else {
      notification['link'] = urlParams;
    }

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
      } else {
        var vfsRoots = grrUi.core.fileDownloadUtils.vfsRoots;
        var isLegitimatePath = vfsRoots.some(function(vfsRoot) {
          return vfsPath.indexOf('/' + vfsRoot + '/') != -1;
        });

        if (!isLegitimatePath) {
          notification['legacyVfsPath'] = true;
        }
      }
    }
  }
};
var annotateApiNotification = module.annotateApiNotification;

/**
 * Creates a link for the notification.
 *
 * @param {Object} notification The notification.
 * @return {Object<string, string>|string} The URL parameters or the URL
 * path for the given notification.
 *
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

  // TODO(user): Get rid of a giant 'if' and refactor to
  // 'handler-by-reference-type' approach.
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
