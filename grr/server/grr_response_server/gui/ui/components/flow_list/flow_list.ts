import {ChangeDetectionStrategy, Component} from '@angular/core';
import {combineLatest, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {Flow, FlowDescriptor, FlowDescriptorMap, FlowListEntry, FlowResultsQuery} from '../../lib/models/flow';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';
import {FlowMenuAction} from '../flow_details/flow_details';



interface FlowListEntryWithDescriptor extends FlowListEntry {
  descriptor?: FlowDescriptor;
}

/** Adds the corresponding FlowDescriptor to a Flow, if existent. */
function withDescriptor(fds: FlowDescriptorMap):
    ((flowListEntry: FlowListEntry) => FlowListEntryWithDescriptor) {
  return flowListEntry => ({
           ...flowListEntry,
           descriptor: fds.get(flowListEntry.flow.name),
         });
}

/** Component that displays executed Flows on the currently selected Client. */
@Component({
  selector: 'flow-list',
  templateUrl: './flow_list.ng.html',
  styleUrls: ['./flow_list.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowList {
  readonly entries$: Observable<ReadonlyArray<FlowListEntryWithDescriptor>> =
      combineLatest([
        this.clientPageFacade.flowListEntries$,
        this.configFacade.flowDescriptors$,
      ]).pipe(map(([flows, fds]) => flows.map(withDescriptor(fds))));

  constructor(
      private readonly configFacade: ConfigFacade,
      private readonly clientPageFacade: ClientPageFacade,
  ) {}

  queryFlowResults(flowId: string, query: FlowResultsQuery) {
    this.clientPageFacade.queryFlowResults(query);
  }

  triggerFlowAction(flow: Flow, event: FlowMenuAction) {
    if (event === FlowMenuAction.DUPLICATE) {
      this.clientPageFacade.startFlowConfiguration(flow.name, flow.args);
      window.scrollTo({top: 0, behavior: 'smooth'});
    } else if (event === FlowMenuAction.CANCEL) {
      this.clientPageFacade.cancelFlow(flow.flowId);
    }
  }

  entryTrackByFunction(index: number, entry: FlowListEntryWithDescriptor) {
    return entry.flow.flowId;
  }
}
