'use strict';

goog.module('grrUi.routing.aff4UrnToUrl');
goog.module.declareLegacyNamespace();

const {CLIENT_ID_RE, stripAff4Prefix} = goog.require('grrUi.core.utils');
const {vfsRoots} = goog.require('grrUi.core.fileDownloadUtils');


// TODO(hanuszczak): Delete suppression once ES6 module migration is complete.
/**
 * @fileoverview
 * @suppress {missingRequire}
 */


/**
 * Returns a router configuration pointing to an AFF4 object with a given
 * URN or undefined if not corresponding href can be generated.
 *
 * @param {string} urn
 * @return {{state: string, params:Object}|null} Object with 2 keys: 'state'
 *     identifying router state and 'params' identifying router params.
 * @export
 */
exports.aff4UrnToUrl = function(urn) {
  var components = stripAff4Prefix(urn).split('/');
  if (CLIENT_ID_RE.test(components[0])) {
    // Handle references to client object or to something within the
    // client namespace: flows or VFS files.

    if (vfsRoots.includes(components[1])) {
      return {
        state: 'client.vfs',
        params: {
          clientId: components[0],
          path: components.slice(1).join('/')
        }
      };
    } else if (components[1] === 'flows' && components.length === 3) {
      return {
        state: 'client.flows',
        params: {
          clientId: components[0],
          flowId: components[2]
        }
      };
    } else {
      return {
        state: 'client',
        params: {
          clientId: components[0]
        }
      };
    }
  } else if (components[0] === 'hunts') {
    // Handle references to hunts.

    return {
      state: 'hunts',
      params: {
        huntId: components[1]
      }
    };
  } else if (components[0] === 'cron') {
    // Handle references to cron jobs.

    return {
      state: 'crons',
      params: {
        cronJobId: components[1]
      }
    };
  } else if (components[0] === 'ACL') {
    // Handle references to approvals.

    if (CLIENT_ID_RE.test(components[1])) {
      return {
        state: 'clientApproval',
        params: {
          clientId: components[1],
          username: components[components.length - 2],
          approvalId: components[components.length - 1]
        }
      };
    } else if (components[1] == 'hunts') {
      return {
        state: 'huntApproval',
        params: {
          huntId: components[2],
          username: components[components.length - 2],
          approvalId: components[components.length - 1]
        }
      };
    } else if (components[1] == 'cron') {
      return {
        state: 'cronJobApproval',
        params: {
          cronJobId: components[2],
          username: components[components.length - 2],
          approvalId: components[components.length - 1]
        }
      };
    }
  }

  return null;
};
