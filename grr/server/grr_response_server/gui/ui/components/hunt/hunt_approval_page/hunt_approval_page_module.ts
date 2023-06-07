import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

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
import {HuntApprovalPageRoutingModule} from './routing';

/**
 * Module for the hunt approval page component.
 */
@NgModule({
  imports: [
    // TODO: Re-enable tslint after migration is complete.
    // tslint:disable:deprecation
    // keep-sorted start block=yes
    CommonModule, MatLegacyButtonModule, MatLegacyCardModule, CopyButtonModule,
    HuntApprovalPageRoutingModule, TextWithLinksModule, UserImageModule,
    HuntFlowArguments, MatLegacyProgressSpinnerModule, MatLegacyTooltipModule,
    HuntOriginalReference, MatLegacyChipsModule, MatIconModule, HuntArguments,
    TimestampModule, FlowArgsViewModule, HelpersModule, HumanReadableSizeModule,
    // keep-sorted end
    // tslint:enable:deprecation
  ],
  declarations: [HuntApprovalPage],
  exports: [HuntApprovalPage]
})
export class HuntApprovalPageModule {
}