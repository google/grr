import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {FileModePipe} from '@app/components/flow_details/helpers/file_mode_pipe';

import {FileResultsTable} from './file_results_table';

import {TimestampModule} from '../../timestamp/module';
import {HumanReadableSizeModule} from '../../human_readable_size/module';



/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    // Angular Material modules.
    ClipboardModule,
    MatButtonModule,
    MatIconModule,
    TimestampModule,
    HumanReadableSizeModule
  ],
  declarations: [
    FileResultsTable,
    FileModePipe,
  ],
  exports: [
    FileResultsTable,
    FileModePipe,
  ],
})
export class HelpersModule {
}
