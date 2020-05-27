import {Type} from '@angular/core';
import {CollectBrowserHistoryForm} from '@app/components/flow_args_form/collect_browser_history_form';
import {CollectMultipleFilesForm} from '@app/components/flow_args_form/collect_multiple_files_form';
import {CollectSingleFileForm} from '@app/components/flow_args_form/collect_single_file_form';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';

import {FallbackFlowArgsForm} from './fallback_flow_args_form';

/** Mapping from flow name to Component class to configure the Flow. */
export const FORMS: {[key: string]: Type<FlowArgumentForm<unknown>>} = {
  'CollectBrowserHistory': CollectBrowserHistoryForm,
  'CollectSingleFile': CollectSingleFileForm,
  'CollectMultipleFiles': CollectMultipleFilesForm,
};

/** Fallback form for Flows without configured form. */
export const DEFAULT_FORM = FallbackFlowArgsForm;
