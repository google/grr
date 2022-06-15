import {CdkTreeModule} from '@angular/cdk/tree';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialogModule} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatRadioModule} from '@angular/material/radio';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatTreeModule} from '@angular/material/tree';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ArtifactCollectorFlowForm} from '../../components/flow_args_form/artifact_collector_flow_form';
import {CollectBrowserHistoryForm} from '../../components/flow_args_form/collect_browser_history_form';
import {CollectMultipleFilesForm} from '../../components/flow_args_form/collect_multiple_files_form';
import {HelpersModule} from '../../components/flow_args_form/collect_multiple_files_form_helpers/module';
import {CollectSingleFileForm} from '../../components/flow_args_form/collect_single_file_form';
import {DumpProcessMemoryForm} from '../../components/flow_args_form/dump_process_memory_form';
import {ByteComponentsModule} from '../../components/form/byte_input/module';
import {DateTimeInputModule} from '../../components/form/date_time_input/module';
import {GlobExpressionExplanationModule} from '../../components/form/glob_expression_form_field/module';
import {CodeEditorModule} from '../code_editor/module';
import {CommaSeparatedInputModule} from '../form/comma_separated_input/module';
import {TimestampModule} from '../timestamp/module';

import {CollectFilesByKnownPathForm} from './collect_files_by_known_path_form';
import {ExecutePythonHackForm} from './execute_python_hack_form';
import {FallbackFlowArgsForm} from './fallback_flow_args_form';
import {FlowArgsForm} from './flow_args_form';
import {LaunchBinaryForm} from './launch_binary_form';
import {ListDirectoryForm} from './list_directory_form';
import {ListNamedPipesForm} from './list_named_pipes_form';
import {ListProcessesForm} from './list_processes_form';
import {NetstatForm} from './netstat_form';
import {OnlineNotificationForm} from './online_notification_form';
import {OsqueryForm} from './osquery_form';
import {OsqueryQueryHelperModule} from './osquery_query_helper/module';
import {ReadLowLevelForm} from './read_low_level_form';
import {TimelineForm} from './timeline_form';
import {ValidationModule} from './validation/validation_module';
import {YaraProcessScanForm} from './yara_process_scan_form';

const FORMS = [
  ArtifactCollectorFlowForm,
  CollectBrowserHistoryForm,
  CollectFilesByKnownPathForm,
  CollectMultipleFilesForm,
  CollectSingleFileForm,
  DumpProcessMemoryForm,
  ExecutePythonHackForm,
  FallbackFlowArgsForm,
  FlowArgsForm,
  LaunchBinaryForm,
  ListDirectoryForm,
  ListNamedPipesForm,
  ListProcessesForm,
  NetstatForm,
  OnlineNotificationForm,
  OsqueryForm,
  ReadLowLevelForm,
  TimelineForm,
  YaraProcessScanForm,
];

/** Module for the FlowArgsForm component. */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,

    CdkTreeModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatCheckboxModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatRadioModule,
    MatSelectModule,
    MatTreeModule,
    MatTooltipModule,

    CodeEditorModule,

    ByteComponentsModule,
    CommaSeparatedInputModule,
    DateTimeInputModule,
    GlobExpressionExplanationModule,
    HelpersModule,
    OsqueryQueryHelperModule,
    TimestampModule,
    ValidationModule,
  ],
  declarations: FORMS,
  entryComponents: FORMS,
  exports: [
    FlowArgsForm,
  ],
})
export class FlowArgsFormModule {
}
