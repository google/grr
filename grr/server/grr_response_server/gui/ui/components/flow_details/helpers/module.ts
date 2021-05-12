import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {ExpandableHashModule} from '@app/components/expandable_hash/module';
import {FileModePipe} from '@app/components/flow_details/helpers/file_mode_pipe';
import {HumanReadableSizeModule} from '@app/components/human_readable_size/module';
import {TimestampModule} from '@app/components/timestamp/module';

import {FileResultsTable} from './file_results_table';
import {OsqueryResultsTable} from './osquery_results_table';
import {ResultAccordion} from './result_accordion';


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
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    // Child component modules
    TimestampModule,
    HumanReadableSizeModule,
    ExpandableHashModule,
  ],
  declarations: [
    FileResultsTable,
    FileModePipe,
    OsqueryResultsTable,
    ResultAccordion,
  ],
  exports: [
    FileResultsTable,
    FileModePipe,
    OsqueryResultsTable,
    ResultAccordion,
  ],
})
export class HelpersModule {
}
