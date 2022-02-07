import {OverlayModule} from '@angular/cdk/overlay';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {MatTooltipModule} from '@angular/material/tooltip';
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
    MatAutocompleteModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatMenuModule,
    MatTooltipModule,
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
