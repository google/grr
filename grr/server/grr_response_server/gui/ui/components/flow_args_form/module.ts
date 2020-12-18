import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {MatDialogModule} from '@angular/material/dialog';
import {MatChipsModule} from '@angular/material/chips';
import {RouterModule} from '@angular/router';
import {CollectBrowserHistoryForm} from '@app/components/flow_args_form/collect_browser_history_form';
import {CollectMultipleFilesForm} from '@app/components/flow_args_form/collect_multiple_files_form';
import {CollectSingleFileForm} from '@app/components/flow_args_form/collect_single_file_form';
import {ByteComponentsModule} from '@app/components/form/byte_input/module';
import {GlobExpressionExplanationModule} from '@app/components/form/glob_expression_form_field/module';

import {FallbackFlowArgsForm} from './fallback_flow_args_form';
import {FlowArgsForm} from './flow_args_form';
import {OsqueryForm} from './osquery_form';
import {CodeEditorModule} from '../code_editor/module';
import {OsqueryQueryHelperModule} from './osquery_query_helper/module';

/** Module for the FlowArgsForm component. */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    MatCheckboxModule,
    MatChipsModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatDialogModule,
    ByteComponentsModule,
    GlobExpressionExplanationModule,
    CodeEditorModule,
    OsqueryQueryHelperModule,
  ],
  declarations: [
    FlowArgsForm,
    CollectBrowserHistoryForm,
    CollectSingleFileForm,
    CollectMultipleFilesForm,
    OsqueryForm,
    FallbackFlowArgsForm,
  ],
  entryComponents: [
    CollectBrowserHistoryForm,
    CollectSingleFileForm,
    CollectMultipleFilesForm,
    OsqueryForm,
    FallbackFlowArgsForm,
  ],
  exports: [
    FlowArgsForm,
  ],
})
export class FlowArgsFormModule {
}
