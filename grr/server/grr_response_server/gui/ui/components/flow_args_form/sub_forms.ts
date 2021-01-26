import {Type} from '@angular/core';
import {ArtifactCollectorFlowForm} from '@app/components/flow_args_form/artifact_collector_flow_form';
import {CollectBrowserHistoryForm} from '@app/components/flow_args_form/collect_browser_history_form';
import {CollectMultipleFilesForm} from '@app/components/flow_args_form/collect_multiple_files_form';
import {CollectSingleFileForm} from '@app/components/flow_args_form/collect_single_file_form';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';

import {FallbackFlowArgsForm} from './fallback_flow_args_form';
import {OsqueryForm} from './osquery_form';
import {TimelineForm} from './timeline_form';

/** Mapping from flow name to Component class to configure the Flow. */
export const FORMS: {[key: string]: Type<FlowArgumentForm<unknown>>} = {
  'ArtifactCollectorFlow': ArtifactCollectorFlowForm,
  'CollectBrowserHistory': CollectBrowserHistoryForm,
  'CollectMultipleFiles': CollectMultipleFilesForm,
  'CollectSingleFile': CollectSingleFileForm,
  'OsqueryFlow': OsqueryForm,
  'TimelineFlow': TimelineForm,

  // Show empty form as fallback for flows that typically do not require
  // configuration.
  'CollectEfiHashes': FallbackFlowArgsForm,
  'CollectRunKeyBinaries': FallbackFlowArgsForm,
  'DumpEfiImage': FallbackFlowArgsForm,
  'DumpFlashImage': FallbackFlowArgsForm,
  'GetClientStats': FallbackFlowArgsForm,
  'GetMBR': FallbackFlowArgsForm,
  'Interrogate': FallbackFlowArgsForm,
  'ListProcesses': FallbackFlowArgsForm,
  'ListVolumeShadowCopies': FallbackFlowArgsForm,
  'Netstat': FallbackFlowArgsForm,
};

/** Fallback form for Flows without configured form. */
export const DEFAULT_FORM = FallbackFlowArgsForm;
