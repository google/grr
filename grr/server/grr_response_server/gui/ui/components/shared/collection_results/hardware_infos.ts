import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {HardwareInfo} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';
import {HardwareInfoDetails} from './data_renderer/hardware_info_details';

function hardwareInfosFromCollectionResults(
  results: readonly CollectionResult[],
): readonly HardwareInfo[] {
  return results.map((item) => item.payload as HardwareInfo);
}

/**
 * Component that shows `HardwareInfo` collection results.
 */
@Component({
  selector: 'hardware-infos',
  templateUrl: './hardware_infos.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, HardwareInfoDetails],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HardwareInfos {
  readonly collectionResults = input.required<
    readonly HardwareInfo[],
    readonly CollectionResult[]
  >({
    transform: hardwareInfosFromCollectionResults,
  });
}
