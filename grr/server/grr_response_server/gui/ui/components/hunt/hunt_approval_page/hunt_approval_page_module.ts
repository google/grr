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
import {HuntArguments} from '../hunt_arguments/hunt_arguments';
import {HuntFlowArguments} from '../hunt_flow_arguments/hunt_flow_arguments';
import {HuntOriginalReference} from '../hunt_original_reference/hunt_original_reference';

import {HuntApprovalPage} from './hunt_approval_page';

/**
 * Module for the hunt approval page component.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    CommonModule,
    CopyButtonModule,
    FlowArgsViewModule,
    HelpersModule,
    HumanReadableSizeModule,
    HuntArguments,
    HuntFlowArguments,
    HuntOriginalReference,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TextWithLinksModule,
    TimestampModule,
    UserImageModule,
    // keep-sorted end
    // clang-format on
  ],
  declarations: [HuntApprovalPage],
  exports: [HuntApprovalPage]
})
export class HuntApprovalPageModule {
}