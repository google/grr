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
import {ApiModule} from '@app/lib/api/module';

import {HelpersModule} from '../helpers/module';

import {CollectBrowserHistoryDetails} from './collect_browser_history_details';
import {CollectMultipleFilesDetails} from './collect_multiple_files_details';
import {CollectSingleFileDetails} from './collect_single_file_details';
import {DefaultDetails} from './default_details';
import {MultiGetFileDetails} from './multi_get_file_details';
import {OsqueryDetails} from './osquery_details';


/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    ApiModule,
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
    CollectMultipleFilesDetails,
    CollectSingleFileDetails,
    OsqueryDetails,
  ],
  exports: [
    DefaultDetails,
    MultiGetFileDetails,
    CollectBrowserHistoryDetails,
    CollectMultipleFilesDetails,
    CollectSingleFileDetails,
    OsqueryDetails,
  ],
  entryComponents: [
    DefaultDetails,
    MultiGetFileDetails,
    CollectBrowserHistoryDetails,
    CollectMultipleFilesDetails,
    CollectSingleFileDetails,
    OsqueryDetails,
  ]
})
export class PluginsModule {
}
