import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyPaginatorModule} from '@angular/material/legacy-paginator';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatLegacyTableModule} from '@angular/material/legacy-table';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {MatSortModule} from '@angular/material/sort';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ExpandableHashModule} from '../../../components/expandable_hash/module';
import {NetworkConnectionFamilyPipe, NetworkConnectionTypePipe} from '../../../components/flow_details/helpers/network_connection_pipes';
import {HumanReadableSizeModule} from '../../../components/human_readable_size/module';
import {TimestampModule} from '../../../components/timestamp/module';
import {FileModeModule} from '../../data_renderers/file_mode/file_mode_module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../../helpers/drawer_link/drawer_link_module';
import {FilterPaginate} from '../../helpers/filter_paginate/filter_paginate';

import {DynamicResultSection} from './dynamic_result_section';
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
    FormsModule,
    ReactiveFormsModule,
    // Angular Material modules.
    ClipboardModule,
    MatLegacyCardModule,
    MatLegacyButtonModule,
    MatLegacyFormFieldModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyProgressSpinnerModule,
    MatSortModule,
    MatLegacyTableModule,
    MatLegacyTooltipModule,
    MatLegacyPaginatorModule,

    CopyButtonModule,
    DrawerLinkModule,
    ExpandableHashModule,
    FileModeModule,
    HumanReadableSizeModule,
    TimestampModule,
    FilterPaginate,
  ],
  declarations: [
    DynamicResultSection,
    FileResultsTable,
    NetworkConnectionFamilyPipe,
    NetworkConnectionTypePipe,
    OsqueryResultsTable,
    ResultAccordion,
    LoadFlowResultsDirective,
    RegistryResultsTable,
  ],
  exports: [
    DynamicResultSection,
    FileResultsTable,
    FilterPaginate,
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
