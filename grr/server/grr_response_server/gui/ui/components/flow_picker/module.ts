import {OverlayModule} from '@angular/cdk/overlay';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyAutocompleteModule} from '@angular/material/legacy-autocomplete';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {FlowsOverview} from '../../components/flow_picker/flows_overview';

import {FlowChips} from './flow_chips';
import {FlowPicker} from './flow_picker';


/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    // Angular modules.
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    ReactiveFormsModule,
    FormsModule,

    // Angular CDK modules.
    OverlayModule,

    // Angular Material modules.
    MatLegacyAutocompleteModule,
    MatLegacyButtonModule,
    MatLegacyCardModule,
    MatIconModule,
    MatLegacyFormFieldModule,
    MatLegacyInputModule,
    MatLegacyMenuModule,
    MatLegacyTooltipModule,
  ],
  declarations: [
    FlowPicker,
    FlowChips,
    FlowsOverview,
  ],
  exports: [
    FlowPicker,
  ],
})
export class FlowPickerModule {
}
