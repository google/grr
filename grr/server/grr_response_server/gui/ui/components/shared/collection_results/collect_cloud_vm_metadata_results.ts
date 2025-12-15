import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {CloudInstance} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {CloudInstanceDetails} from './data_renderer/cloud_instance_details';

/**
 * Component that shows `CollectCloudVmMetadata` flow results.
 */
@Component({
  selector: 'collect-cloud-vm-metadata-results',
  templateUrl: './collect_cloud_vm_metadata_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CloudInstanceDetails, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectCloudVmMetadataResults {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected cloudInstanceFromCollectionResult(
    result: CollectionResult,
  ): CloudInstance {
    return result.payload as CloudInstance;
  }
}
