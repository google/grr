import {Type} from '@angular/core';
import {BrowserHistoryFlowForm} from '@app/components/flow_args_form/browser_history_flow_form';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {FallbackFlowArgsForm} from './fallback_flow_args_form';

/** Mapping from flow name to Component class to configure the Flow. */
export const FORMS: {[key: string]: Type<FlowArgumentForm<unknown>>} = {
  'BrowserHistoryFlow': BrowserHistoryFlowForm,
};

/** Fallback form for Flows without configured form. */
export const DEFAULT_FORM = FallbackFlowArgsForm;
