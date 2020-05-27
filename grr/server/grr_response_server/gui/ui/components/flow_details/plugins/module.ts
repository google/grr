import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatExpansionModule} from '@angular/material/expansion';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {HelpersModule} from '../helpers/module';
import {CollectBrowserHistoryDetails} from './collect_browser_history_details';
import {DefaultDetails} from './default_details';
import {MultiGetFileDetails} from './multi_get_file_details';


/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    MatButtonModule,
    MatCardModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatMenuModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    ReactiveFormsModule,
    FormsModule,
    MatInputModule,
    MatCardModule,
    HelpersModule,
  ],
  declarations: [
    DefaultDetails,
    MultiGetFileDetails,
    CollectBrowserHistoryDetails,
  ],
  exports: [
    DefaultDetails,
    MultiGetFileDetails,
    CollectBrowserHistoryDetails,
  ],
  entryComponents: [
    DefaultDetails,
    MultiGetFileDetails,
    CollectBrowserHistoryDetails,
  ]
})
export class PluginsModule {
}
