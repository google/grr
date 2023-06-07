import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

import {ApprovalCardModule} from '../../approval_card/module';
import {FlowDetailsModule} from '../../flow_details/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {HuntFlowArguments} from '../hunt_flow_arguments/hunt_flow_arguments';
import {HuntHelpModule} from '../hunt_help/module';
import {HuntOriginalReference} from '../hunt_original_reference/hunt_original_reference';

import {ClientsFormModule} from './clients_form/module';
import {NewHunt} from './new_hunt';
import {OutputPluginsFormModule} from './output_plugins_form/module';
import {ParamsFormModule} from './params_form/module';
import {NewHuntRoutingModule} from './routing';

/**
 * Module for new hunt creation.
 */
@NgModule({
  imports: [
    // TODO: Re-enable tslint after migration is complete.
    // tslint:disable:deprecation
    // keep-sorted start block=yes
    ApprovalCardModule,
    ClientsFormModule,
    CommonModule,
    CopyButtonModule,
    FlowDetailsModule,
    FormsModule,
    HuntFlowArguments,
    HuntHelpModule,
    HuntOriginalReference,
    MatIconModule,
    MatLegacyButtonModule,
    MatLegacyChipsModule,
    MatLegacyFormFieldModule,
    MatLegacyInputModule,
    MatLegacyTooltipModule,
    NewHuntRoutingModule,
    OutputPluginsFormModule,
    ParamsFormModule,
    ReactiveFormsModule,
    // keep-sorted end
    // tslint:enable:deprecation
  ],
  declarations: [NewHunt],
})
export class NewHuntModule {
}
