import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatTableModule} from '@angular/material/table';

import {FLOW_PAYLOAD_TYPE_TRANSLATION} from '../../../lib/api_translation/result';
import {ExpandableHashModule} from '../../expandable_hash/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../../helpers/drawer_link/drawer_link_module';
import {FilterPaginate} from '../../helpers/filter_paginate/filter_paginate';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';
import {UserImageModule} from '../../user_image/module';
import {FileModeModule} from '../file_mode/file_mode_module';

import {DataTableView} from './table';

/** Component to show a data table with flow results. */
@Component({
  selector: 'app-flow-data-table',
  templateUrl: './table.ng.html',
  styleUrls: ['./table.scss'],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,

    MatButtonModule,
    MatIconModule,
    MatTableModule,

    FilterPaginate,
    TimestampModule,
    CopyButtonModule,
    DrawerLinkModule,
    ExpandableHashModule,
    FileModeModule,
    HumanReadableSizeModule,
    UserImageModule,
  ],
})
export class FlowDataTableView<T> extends DataTableView<T> {
  protected override getPayloadTypeTranslation(type: string) {
    const translation =
        FLOW_PAYLOAD_TYPE_TRANSLATION[type as keyof typeof FLOW_PAYLOAD_TYPE_TRANSLATION];

    // If there is no "Flow" definition for the Payload Type translation,
    // we fall back to the "Hunt" translation:
    if (!translation) return super.getPayloadTypeTranslation(type);

    return translation;
  }
}