'use strict';

goog.module('grrUi.routing.rewriteUrlTest');

const {rewriteUrl} = goog.require('grrUi.routing.rewriteUrl');


describe('rewriteUrl()', () => {
  const mapping = {};

  // Crons.
  mapping['main=ManageCron'] = '/crons/';
  mapping['main=ManageCron&cron_job_urn=aff4:/cron/CleanTemp'] = '/crons/CleanTemp';

  // Hunts.
  mapping['main=ManageHunts'] = '/hunts/';
  mapping['main=ManageHunts&hunt_id=aff4:/hunts/H:123456'] = '/hunts/H:123456';

  // Virtual File System.
  mapping['main=VirtualFileSystemView&c=C.dc1a70ddaaba407a&tag=AFF4Stats' +
      '&t=_fs-tsk-_5C_5C_3F_5CVolume_7B649ac6fa_2D9ab4_' +
      '2D11e5_2Db332_2D806e6f6e6963_7D'] = '/clients/C.dc1a70ddaaba407a/vfs/fs/tsk/' +
          '%5C%5C%3F%5CVolume%7B649ac6fa-9ab4-11e5-b332-806e6f6e6963%7D/';

  // Misc.
  mapping['main=GlobalLaunchFlows'] = '/global-flows';
  mapping['main=ServerLoadView'] = '/server-load';
  mapping['main=BinaryConfigurationView'] = '/manage-binaries';
  mapping['main=ConfigManager'] = '/config';
  mapping['main=ArtifactManagerView'] = '/artifacts';
  mapping['main=ApiDocumentation'] = '/api-docs';

  // ACL checks.
  mapping['main=GrantAccess&acl=' +
      'aff4%3A%2FACL%2Fhunts%2FH%3A55AAAA70%2Ftest%2Fapproval%3A6AFF3CC9'] =
      '/users/test/approvals/hunt/H:55AAAA70/approval:6AFF3CC9';
  mapping['main=GrantAccess&acl=' +
      'aff4%3A%2FACL%2FC.833c593a0fe6aca0%2Ftest%2Fapproval%3A8935BE23'] =
      '/users/test/approvals/client/C.833c593a0fe6aca0/approval:8935BE23';

  // Canary test.
  mapping['main=CanaryTestRenderer'] = '/canary-test';

  // HostTable.
  mapping['main=HostTable'] = '/search?q=';
  mapping['main=HostTable&q=test'] = '/search?q=test';

  it('should map legacy URLs to correct sane URLs', () => {
    angular.forEach(mapping, (targetUrl, legacyUrl) => {
      expect(rewriteUrl(legacyUrl)).toEqual(targetUrl);
    });
  });
});


exports = {};
