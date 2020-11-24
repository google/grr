import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {UserImageModule} from '../user_image/module';

import {FlowDetails} from './flow_details';
import {HelpersModule} from './helpers/module';
import {PluginsModule} from './plugins/module';



/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    ClipboardModule,
    CommonModule,
    FormsModule,
    HelpersModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    PluginsModule,
    ReactiveFormsModule,
    RouterModule,
    UserImageModule,
  ],
  declarations: [
    FlowDetails,
  ],
  exports: [
    FlowDetails,
  ],
})
export class FlowDetailsModule {
}
