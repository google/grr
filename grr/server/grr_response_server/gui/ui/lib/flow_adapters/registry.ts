import {FlowDetailsAdapter} from './adapter';
import {TimelineAdapter} from './filesystem';
import {ListProcessesAdapter} from './list_processes';

/** The fallback adapter to use when FLOW_ADAPTER does not contain a flow. */
export const DEFAULT_ADAPTER = new FlowDetailsAdapter();

/** Lookup table from flow name to FlowDetailsAdapter instance. */
export const FLOW_ADAPTERS:
    {readonly [flowName: string]: FlowDetailsAdapter|undefined} = {
      'ListProcesses': new ListProcessesAdapter(),
      'Timeline': new TimelineAdapter(),
    };
