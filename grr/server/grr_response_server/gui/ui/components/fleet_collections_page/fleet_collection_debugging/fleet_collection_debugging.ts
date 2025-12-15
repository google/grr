import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input as routerInput,
} from '@angular/core';
import {Title} from '@angular/platform-browser';

import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {FleetCollectionLogs} from './fleet_collection_logs';

/** Component that displays debugging information of a single fleet collection. */
@Component({
  selector: 'fleet-collection-debugging',
  templateUrl: './fleet_collection_debugging.ng.html',
  styleUrls: ['./fleet_collection_debugging.scss'],
  imports: [CommonModule, FleetCollectionLogs],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionDebugging {
  protected readonly fleetCollectionStore = inject(FleetCollectionStore);

  fleetCollectionId = routerInput<string | undefined>();

  constructor() {
    inject(Title).setTitle('GRR | Fleet Collection > Debugging');
  }

  protected stringify(data: unknown) {
    return JSON.stringify(
      data,
      (_, v) => (typeof v === 'bigint' ? v.toString() : v),
      2,
    );
  }
}
