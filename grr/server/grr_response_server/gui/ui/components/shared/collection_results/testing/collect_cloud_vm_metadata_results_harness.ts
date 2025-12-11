import {ComponentHarness} from '@angular/cdk/testing';

import {CloudInstanceDetailsHarness} from '../data_renderer/testing/cloud_instance_details_harness';

/** Harness for the CollectCloudVmMetadataResults component. */
export class CollectCloudVmMetadataResultsHarness extends ComponentHarness {
  static hostSelector = 'collect-cloud-vm-metadata-results';

  readonly clientIds = this.locatorForAll('.client-id');

  readonly cloudInstanceDetailsHarnesses = this.locatorForAll(
    CloudInstanceDetailsHarness,
  );
}
