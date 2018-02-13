'use strict';

goog.module('grrUi.routing.rewriteUrl');
goog.module.declareLegacyNamespace();

const {aff4UrnToUrl} = goog.require('grrUi.routing.aff4UrnToUrl');
const {encodeUrlPath} = goog.require('grrUi.core.apiService');
const {ensurePathIsFolder} = goog.require('grrUi.client.virtualFileSystem.utils');
const {getFilePathFromId} = goog.require('grrUi.client.virtualFileSystem.fileViewDirective');


/**
 * Parses the location bar's #hash value into an object.
 *
 * @param {string} hash Hash to be parsed.
 * @return {Object} an associative array of encoded values.
 */
const parseHash = function(hash) {
  if (hash.indexOf('#') == 0) {
    hash = hash.substr(1);
  }

  var result = {};
  var parts = hash.split('&');

  for (var i = 0; i < parts.length; i++) {
    var kv = parts[i].split('=');
    if (kv[0] && kv[1]) {
      result[kv[0]] = decodeURIComponent(kv[1].replace(/\+/g, ' ') || '');
    }
  }

  return result;
};

/**
 * Rewrites legacy URLs to URLs compatible with the new URL scheme.
 *
 * @param {string} url The URL to rewrite.
 * @return {?string} A URL compatible with UI router.
 * @export
 */
exports.rewriteUrl = function(url) {
  var hashState = parseHash(url);

  var clientId = hashState['c'];
  if (clientId && clientId.indexOf('aff4:/') === 0) {
    clientId = clientId.split('/')[1];
  }

  var main = hashState['main'];
  switch(main) {
      //
      // Management redirects.
      //

    case 'ManageCron':
      var cronJobUrn = hashState['cron_job_urn'];
      var cronJobId = cronJobUrn ? cronJobUrn.split('/')[2] : '';
      return '/crons/' + cronJobId;

    case 'ManageHunts':
      var huntUrn = hashState['hunt_id'];
      var huntId = huntUrn ? huntUrn.split('/')[2] : '';
      return '/hunts/' + huntId;

    case 'GlobalLaunchFlows':
      return '/global-flows';

    case 'ServerLoadView':
      return '/server-load';

      //
      // Configuration redirects.
      //

    case 'BinaryConfigurationView':
      return '/manage-binaries';

    case 'ConfigManager':
      return '/config';

    case 'ArtifactManagerView':
      return '/artifacts';

      //
      // Misc. redirects.
      //

    case 'ApiDocumentation':
      return '/api-docs';

    // TODO(user): get rid of GrantAccess rewrite as soon as links in
    // previously send approval notifications are not important.
    case 'GrantAccess':
      var acl = hashState['acl'] || '';
      var routingState = aff4UrnToUrl(acl);
      switch (routingState['state']) {
        case 'clientApproval':
          return ['/users',
                  routingState['params']['username'],
                  'approvals',
                  'client',
                  routingState['params']['clientId'],
                  routingState['params']['approvalId']].join('/');
        case 'huntApproval':
          return ['/users',
                  routingState['params']['username'],
                  'approvals',
                  'hunt',
                  routingState['params']['huntId'],
                  routingState['params']['approvalId']].join('/');

        case 'cronJobApproval':
          return ['/users',
                  routingState['params']['username'],
                  'approvals',
                  'cron-job',
                  routingState['params']['cronJobId'],
                  routingState['params']['approvalId']].join('/');

        default:
          break;
      }
      return '/';

    case 'CanaryTestRenderer':
      return '/canary-test';

      //
      // Client redirects.
      //

    case 'HostTable':
      var q = hashState['q'] || '';
      return '/search?q=' + q;

    case 'HostInformation':
      return '/clients/' + clientId;

    case 'VirtualFileSystemView':
      var path;
      if (hashState['aff4_path']) {
        path = hashState['aff4_path'].slice(
            hashState['c'].length + 1);
      } else {
        path = ensurePathIsFolder(getFilePathFromId(hashState['t'] || ''));
      }
      return '/clients/' + clientId + '/vfs/' + encodeUrlPath(path);

    case 'TimelineMain':
    case 'ContainerViewer':
      var path = hashState['container'] || '';
      var query = hashState['query'] || '';
      return '/clients/' + clientId + '/vfs-container' +
        '?path=' + path + '&query=' + query;

    case 'LaunchFlows':
      return '/clients/' + clientId + '/launch-flow';

    case 'ManageFlows':
      var flowUrn = hashState['flow'];
      var flowId = flowUrn ? flowUrn.split('/')[3] : '';
      return '/clients/' + clientId + '/flows/' + flowId;

    case 'DebugClientRequestsView':
      return '/clients/' + clientId + '/debug-requests';

    case 'ClientLoadView':
      return '/clients/' + clientId + '/load';

    case 'ClientCrashesRenderer':
      return '/clients/' + clientId + '/crashes';

    case 'ClientStatsView':
      return '/clients/' + clientId + '/stats';

    default:
      // If we do not have a main field, but a client id, show the host
      // info for the client.
      if (clientId) {
        return '/clients/' + clientId;
      }

      // Otherwise, we assume the URL is already in the new format and
      // do no rewriting.
      return null;
  }
};
