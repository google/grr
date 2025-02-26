import {ClipboardModule} from '@angular/cdk/clipboard';
import {CdkTreeModule} from '@angular/cdk/tree';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {MatExpansionModule} from '@angular/material/expansion';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSortModule} from '@angular/material/sort';
import {MatTableModule} from '@angular/material/table';
import {MatTabsModule} from '@angular/material/tabs';
import {MatTreeModule} from '@angular/material/tree';
import {RouterModule} from '@angular/router';

import {ApiModule} from '../../../lib/api/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../../helpers/drawer_link/drawer_link_module';
import {FilterPaginate} from '../../helpers/filter_paginate/filter_paginate';
import {TimestampModule} from '../../timestamp/module';
import {HelpersModule} from '../helpers/module';

import {ProcessView} from '../../data_renderers/process/process_view';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {ArtifactCollectorFlowDetails} from './artifact_collector_flow_details';
import {CollectBrowserHistoryDetails} from './collect_browser_history_details';
import {CollectFilesByKnownPathDetails} from './collect_files_by_known_path_details';
import {CollectLargeFileFlowDetails} from './collect_large_file_flow_details';
import {CollectMultipleFilesDetails} from './collect_multiple_files_details';
import {DefaultDetails} from './default_details';
import {DumpProcessMemoryDetails} from './dump_process_memory_details';
import {ExecutePythonHackDetails} from './execute_python_hack_details';
import {FileFinderDetails} from './file_finder_details';
import {HashMultipleFilesDetails} from './hash_multiple_files_details';
import {InterrogateDetails} from './interrogate_details';
import {LaunchBinaryDetails} from './launch_binary_details';
import {ListDirectoryDetails} from './list_directory_details';
import {ListProcessesDetails} from './list_processes_details';
import {MultiGetFileDetails} from './multi_get_file_details';
import {NetstatDetails} from './netstat_details';
import {OnlineNotificationDetails} from './online_notification_details';
import {OsqueryDetails} from './osquery_details';
import {ReadLowLevelDetails} from './read_low_level_details';
import {StatMultipleFilesDetails} from './stat_multiple_files_details';
import {TimelineDetails} from './timeline_details';
import {YaraProcessScanDetails} from './yara_process_scan_details';

const COMPONENTS = [
  // TODO: re-enable clang format when solved.
  // prettier-ignore
  // keep-sorted start block=yes
  ArtifactCollectorFlowDetails,
  CollectBrowserHistoryDetails,
  CollectFilesByKnownPathDetails,
  CollectLargeFileFlowDetails,
  CollectMultipleFilesDetails,
  DefaultDetails,
  DumpProcessMemoryDetails,
  ExecutePythonHackDetails,
  FileFinderDetails,
  HashMultipleFilesDetails,
  InterrogateDetails,
  LaunchBinaryDetails,
  ListDirectoryDetails,
  ListProcessesDetails,
  MultiGetFileDetails,
  NetstatDetails,
  OnlineNotificationDetails,
  OsqueryDetails,
  ReadLowLevelDetails,
  StatMultipleFilesDetails,
  TimelineDetails,
  YaraProcessScanDetails,
  // keep-sorted end
];

/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    ApiModule,
    CdkTreeModule,
    ClipboardModule,
    CommonModule,
    CopyButtonModule,
    DrawerLinkModule,
    FilterPaginate,
    FormsModule,
    HelpersModule,
    HumanReadableSizeModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatChipsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSortModule,
    MatTableModule,
    MatTabsModule,
    MatTreeModule,
    ProcessView,
    ReactiveFormsModule,
    RouterModule,
    TimestampModule,
    // keep-sorted end
  ],
  declarations: COMPONENTS,
  exports: COMPONENTS,
})
export class PluginsModule {}
