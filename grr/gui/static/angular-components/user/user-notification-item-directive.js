'use strict';

goog.provide('grrUi.user.userNotificationItemDirective.UserNotificationItemController');
goog.provide('grrUi.user.userNotificationItemDirective.UserNotificationItemDirective');

goog.scope(function() {

var module = grrUi.user.userNotificationItemDirective;


/**
 * Controller for UserNotificationItemDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$window} $window
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
module.UserNotificationItemController =
  function($scope, $window, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$window} */
  this.window_ = $window;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.scope_.$watch('notification', this.onNotificationChanged_.bind(this));
};

var UserNotificationItemController = module.UserNotificationItemController;


/**
 * Prepares the notification for displaying.
 *
 * @param {Object} notification
 * @private
 */
UserNotificationItemController.prototype.onNotificationChanged_ = function(notification){
  var urlParams = this.getUrlParameters_(notification);
  notification['isPending'] = notification['value']['is_pending']['value'];
  if (urlParams) {
    notification['link'] = $.param(urlParams);
    notification['isFileDownload'] = urlParams['main'] === 'DownloadFile';
    notification['refType'] = notification['value']['reference']['value']['type']['value'];
    if (notification['isFileDownload']) {
      notification['path'] = urlParams['aff4_path'];
    }
  }
};

/**
 * Creates a link for the notification.
 *
 * @param {Object} fullNotification
 * @private
 */
UserNotificationItemController.prototype.getUrlParameters_ = function(fullNotification){
  var notification = this.grrApiService_.stripTypeInfo(fullNotification);
  var reference = notification['reference'];
  var referenceType = reference['type'];
  if (!referenceType) {
    return null;
  }

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
      urlParameters['t'] = this.createTreeString_(referenceDetails['vfs_path']);
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
 * Creates a tree string for a notification containing a VFS path.
 *
 * @param {string} vfsPath
 * @private
 */
UserNotificationItemController.prototype.createTreeString_ = function(vfsPath){
  // The directory path looks like aff4:/<client>/<path>/<path>/...
  var components = vfsPath.split('/').slice(2, -1);
  var result = components.map(this.replaceInvalidChars_.bind(this));
  return '_' + result.join('-');
}

/**
 * Replaces all non-alphanumeric characters with their hex representation.
 *
 * @param {string} item
 * @private
 */
UserNotificationItemController.prototype.replaceInvalidChars_ = function(item){
  return item.replace(/[^a-zA-Z0-9]/g, function(invChar){
    var hex = invChar.charCodeAt(0).toString(16);
    return '_' + hex.toUpperCase();
  });
}

/**
 * Opens the reference of the notification.
 *
 * @export
 */
UserNotificationItemController.prototype.openReference = function(){
  var notification = this.scope_['notification']
  if (!notification['isFileDownload'] && notification['link']) {
    this.window_.location.href = '#' + notification['link'];
    this.window_.location.reload();
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
      notification: '='
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