import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {CloudInstance} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';
import {CloudInstanceDetails} from './data_renderer/cloud_instance_details';

function cloudInstanceFromCollectionResults(
  results: readonly CollectionResult[],
): readonly CloudInstance[] {
  return results.map((item) => item.payload as CloudInstance);
}

/**
 * Component that shows `CollectCloudVmMetadata` flow results.
 */
@Component({
  selector: 'collect-cloud-vm-metadata-results',
  templateUrl: './collect_cloud_vm_metadata_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CloudInstanceDetails],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectCloudVmMetadataResults {
  readonly collectionResults = input.required<
    readonly CloudInstance[],
    readonly CollectionResult[]
  >({
    transform: cloudInstanceFromCollectionResults,
  });
}
