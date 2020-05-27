import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {CollectBrowserHistoryForm} from '@app/components/flow_args_form/collect_browser_history_form';
import {CollectMultipleFilesForm} from '@app/components/flow_args_form/collect_multiple_files_form';
import {CollectSingleFileForm} from '@app/components/flow_args_form/collect_single_file_form';
import {ByteComponentsModule} from '@app/components/form/byte_input/module';

import {FallbackFlowArgsForm} from './fallback_flow_args_form';
import {FlowArgsForm} from './flow_args_form';

/** Module for the FlowArgsForm component. */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    MatCheckboxModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    ByteComponentsModule,
  ],
  declarations: [
    FlowArgsForm,
    CollectBrowserHistoryForm,
    CollectSingleFileForm,
    CollectMultipleFilesForm,
    FallbackFlowArgsForm,
  ],
  entryComponents: [
    CollectBrowserHistoryForm,
    CollectSingleFileForm,
    CollectMultipleFilesForm,
    FallbackFlowArgsForm,
  ],
  exports: [
    FlowArgsForm,
  ],
})
export class FlowArgsFormModule {
}
