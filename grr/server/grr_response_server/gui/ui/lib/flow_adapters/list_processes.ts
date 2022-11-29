import {ProcessView} from '../../components/data_renderers/process/process_view';
import {ListProcessesArgs} from '../api/api_interfaces';
import {Flow, FlowResultCount} from '../models/flow';
import {capitalize} from '../type_utils';

import {FlowDetailsAdapter, FlowResultSection} from './adapter';

/** Adapter for ListProcesses flow. */
export class ListProcessesAdapter extends
    FlowDetailsAdapter<Flow<ListProcessesArgs>> {
  private getArgDescription(args?: ListProcessesArgs): string {
    const conditions: string[] = [];

    if (args?.pids?.length) {
      conditions.push(`PID matching ${args.pids.join(', ')}`);
    }

    if (args?.filenameRegex) {
      conditions.push(`executable matching ${args.filenameRegex}`);
    }

    if (args?.connectionStates?.length) {
      conditions.push(`connections in ${args.connectionStates.join(', ')}`);
    }

    if (conditions.length) {
      return capitalize(conditions.join(' and '));
    } else {
      return 'All processes';
    }
  }

  override getResultView(
      resultGroup: FlowResultCount,
      args: ListProcessesArgs|undefined): FlowResultSection|undefined {
    if (resultGroup.type === 'Process') {
      return {
        title: this.getArgDescription(args),
        component: ProcessView,
        query: {type: resultGroup.type},
      };
    } else {
      return super.getResultView(resultGroup, args);
    }
  }
}
