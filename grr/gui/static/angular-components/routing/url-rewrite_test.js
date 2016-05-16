'use strict';

goog.require('grrUi.routing.rewriteUrl');

var rewriteUrl = grrUi.routing.rewriteUrl;

describe('rewriteUrl()', function() {

  var mapping = {};

  // Crons.
  mapping['main=ManageCron'] = '/crons/';
  mapping['main=ManageCron&cron_job_urn=aff4:/cron/CleanTemp'] = '/crons/CleanTemp';

  // Hunts.
  mapping['main=ManageHunts'] = '/hunts/';
  mapping['main=ManageHunts&hunt_id=aff4:/hunts/H:123456'] = '/hunts/H:123456';

  // Hunt Details.
  mapping['main=ManageHuntsClientView'] = '/hunt-details/';
  mapping['main=ManageHuntsClientView&hunt_id=aff4:/hunts/H:123456'] = '/hunt-details/H:123456';

  // Statistics.
  mapping['main=ShowStatistics'] = '/stats?selection=';
  mapping['main=ShowStatistics&t=test'] = '/stats?selection=test';

  // Misc.
  mapping['main=GlobalLaunchFlows'] = '/global-flows';
  mapping['main=ServerLoadView'] = '/server-load';
  mapping['main=GlobalCrashesRenderer'] = '/client-crashes';
  mapping['main=BinaryConfigurationView'] = '/manage-binaries';
  mapping['main=ConfigManager'] = '/config';
  mapping['main=ArtifactManagerView'] = '/artifacts';
  mapping['main=ApiDocumentation'] = '/api-docs';

  // ACL checks.
  mapping['main=GrantAccess'] = '/grant-access?acl=';
  mapping['main=GrantAccess&acl=test'] = '/grant-access?acl=test';

  // Canary test.
  mapping['main=CanaryTestRenderer'] = '/canary-test';

  // ACL checks.
  mapping['main=GrantAccess'] = '/grant-access?acl=';
  mapping['main=GrantAccess&acl=test'] = '/grant-access?acl=test';

  // RDFValueCollection.
  mapping['main=RDFValueCollectionRenderer'] = '/rdf-collection?path=';
  mapping['main=RDFValueCollectionRenderer&aff4_path=test'] = '/rdf-collection?path=test';

  // HostTable.
  mapping['main=HostTable'] = '/search?q=';
  mapping['main=HostTable&q=test'] = '/search?q=test';

  it('should map legacy URLs to correct sane URLs', function() {
    angular.forEach(mapping, function(targetUrl, legacyUrl) {
      expect(rewriteUrl(legacyUrl)).toEqual(targetUrl);
    });
  });
});