import {ComponentHarness} from '@angular/cdk/testing';

import {HardwareInfoDetailsHarness} from '../data_renderer/testing/hardware_info_details_harness';

/** Harness for the HardwareInfos component. */
export class HardwareInfosHarness extends ComponentHarness {
  static hostSelector = 'hardware-infos';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly hardwareInfoDetailsHarnesses = this.locatorForAll(
    HardwareInfoDetailsHarness,
  );
}
