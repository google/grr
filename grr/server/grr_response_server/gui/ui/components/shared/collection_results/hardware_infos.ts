import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {HardwareInfo} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {HardwareInfoDetails} from './data_renderer/hardware_info_details';

/**
 * Component that shows `HardwareInfo` collection results.
 */
@Component({
  selector: 'hardware-infos',
  templateUrl: './hardware_infos.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CopyButton, HardwareInfoDetails],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HardwareInfos {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected hardwareInfoFromCollectionResult(
    result: CollectionResult,
  ): HardwareInfo {
    return result.payload as HardwareInfo;
  }
}
