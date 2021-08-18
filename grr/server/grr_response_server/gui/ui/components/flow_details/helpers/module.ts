import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTableModule} from '@angular/material/table';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {ExpandableHashModule} from '@app/components/expandable_hash/module';
import {FileModePipe} from '@app/components/flow_details/helpers/file_mode_pipe';
import {NetworkConnectionFamilyPipe, NetworkConnectionTypePipe} from '@app/components/flow_details/helpers/network_connection_pipes';
import {HumanReadableSizeModule} from '@app/components/human_readable_size/module';
import {TimestampModule} from '@app/components/timestamp/module';

import {DrawerLinkModule} from '../../helpers/drawer_link/drawer_link_module';

import {FileResultsTable} from './file_results_table';
import {LoadFlowResultsDirective} from './load_flow_results_directive';
import {OsqueryResultsTable} from './osquery_results_table';
import {RegistryResultsTable} from './registry_results_table';
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
    MatProgressSpinnerModule,
    MatTableModule,

    DrawerLinkModule,
    ExpandableHashModule,
    HumanReadableSizeModule,
    TimestampModule,
  ],
  declarations: [
    FileResultsTable,
    FileModePipe,
    NetworkConnectionFamilyPipe,
    NetworkConnectionTypePipe,
    OsqueryResultsTable,
    ResultAccordion,
    LoadFlowResultsDirective,
    RegistryResultsTable,
  ],
  exports: [
    FileResultsTable,
    FileModePipe,
    NetworkConnectionFamilyPipe,
    NetworkConnectionTypePipe,
    OsqueryResultsTable,
    ResultAccordion,
    LoadFlowResultsDirective,
    RegistryResultsTable,
  ],
})
export class HelpersModule {
}
