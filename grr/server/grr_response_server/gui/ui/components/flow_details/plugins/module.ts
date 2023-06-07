import {ClipboardModule} from '@angular/cdk/clipboard';
import {CdkTreeModule} from '@angular/cdk/tree';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatExpansionModule} from '@angular/material/expansion';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyCheckboxModule} from '@angular/material/legacy-checkbox';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatLegacyTableModule} from '@angular/material/legacy-table';
import {MatLegacyTabsModule} from '@angular/material/legacy-tabs';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatSortModule} from '@angular/material/sort';
import {MatTreeModule} from '@angular/material/tree';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ApiModule} from '../../../lib/api/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../../helpers/drawer_link/drawer_link_module';
import {FilterPaginate} from '../../helpers/filter_paginate/filter_paginate';
import {TimestampModule} from '../../timestamp/module';
import {HelpersModule} from '../helpers/module';

import {ArtifactCollectorFlowDetails} from './artifact_collector_flow_details';
import {CollectBrowserHistoryDetails} from './collect_browser_history_details';
import {CollectFilesByKnownPathDetails} from './collect_files_by_known_path_details';
import {CollectMultipleFilesDetails} from './collect_multiple_files_details';
import {CollectSingleFileDetails} from './collect_single_file_details';
import {DefaultDetails} from './default_details';
import {DumpProcessMemoryDetails} from './dump_process_memory_details';
import {ExecutePythonHackDetails} from './execute_python_hack_details';
import {FileFinderDetails} from './file_finder_details';
import {InterrogateDetails} from './interrogate_details';
import {LaunchBinaryDetails} from './launch_binary_details';
import {ListDirectoryDetails} from './list_directory_details';
import {MultiGetFileDetails} from './multi_get_file_details';
import {NetstatDetails} from './netstat_details';
import {OnlineNotificationDetails} from './online_notification_details';
import {OsqueryDetails} from './osquery_details';
import {ReadLowLevelDetails} from './read_low_level_details';
import {YaraProcessScanDetails} from './yara_process_scan_details';


const COMPONENTS = [
  ArtifactCollectorFlowDetails,
  CollectBrowserHistoryDetails,
  CollectFilesByKnownPathDetails,
  CollectMultipleFilesDetails,
  CollectSingleFileDetails,
  DefaultDetails,
  DumpProcessMemoryDetails,
  ExecutePythonHackDetails,
  FileFinderDetails,
  InterrogateDetails,
  LaunchBinaryDetails,
  ListDirectoryDetails,
  MultiGetFileDetails,
  NetstatDetails,
  OnlineNotificationDetails,
  OsqueryDetails,
  ReadLowLevelDetails,
  YaraProcessScanDetails,
];

/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    ApiModule,
    BrowserAnimationsModule,
    ClipboardModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    CdkTreeModule,
    MatLegacyButtonModule,
    MatLegacyCardModule,
    MatLegacyChipsModule,
    MatLegacyCheckboxModule,
    MatExpansionModule,
    MatLegacyFormFieldModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyMenuModule,
    MatProgressBarModule,
    MatLegacyProgressSpinnerModule,
    MatLegacyTableModule,
    MatLegacyTabsModule,
    MatSortModule,
    MatTreeModule,
    CopyButtonModule,
    DrawerLinkModule,
    HelpersModule,
    TimestampModule,
    FilterPaginate,
  ],
  declarations: COMPONENTS,
  exports: COMPONENTS
})
export class PluginsModule {
}
