import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTooltipModule} from '@angular/material/tooltip';

import {FlowArgsViewModule} from '../../flow_args_view/module';
import {HelpersModule} from '../../flow_details/helpers/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {TextWithLinksModule} from '../../helpers/text_with_links/text_with_links_module';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';
import {UserImageModule} from '../../user_image/module';

import {HuntApprovalPage} from './hunt_approval_page';
import {HuntApprovalPageRoutingModule} from './routing';

/**
 * Module for the hunt approval page component.
 */
@NgModule({
  imports: [
    CommonModule,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatChipsModule,
    MatIconModule,

    HuntApprovalPageRoutingModule,
    TextWithLinksModule,
    UserImageModule,
    CopyButtonModule,
    TimestampModule,
    FlowArgsViewModule,
    HelpersModule,
    HumanReadableSizeModule,

  ],
  declarations: [HuntApprovalPage],
  exports: [HuntApprovalPage]
})
export class HuntApprovalPageModule {
}