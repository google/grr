import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';

import {StartupInfo} from '../../../../lib/models/client';
import {Timestamp} from '../../timestamp';

/**
 * Component displaying the startup info.
 */
@Component({
  selector: 'startup-info-details',
  templateUrl: './startup_info_details.ng.html',
  styleUrls: ['./snapshot_tables.scss'],
  imports: [CommonModule, MatChipsModule, MatIconModule, Timestamp],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StartupInfoDetails {
  readonly startupInfo = input.required<StartupInfo | undefined>();
}
