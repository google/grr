import {ChangeDetectionStrategy, Component} from '@angular/core';
import {combineLatest, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {Flow, FlowDescriptor, FlowListEntry} from '../../lib/models/flow';
import {ClientFacade} from '../../store/client_facade';
import {FlowDescriptorMap} from '../../store/flow/flow_reducers';
import {FlowFacade} from '../../store/flow_facade';
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
        this.clientFacade.flowListEntries$,
        this.flowFacade.flowDescriptors$,
      ]).pipe(map(([flows, fds]) => flows.map(withDescriptor(fds))));

  constructor(
      private readonly flowFacade: FlowFacade,
      private readonly clientFacade: ClientFacade,
  ) {}

  toggleFlowExpansion(flowId: string) {
    this.clientFacade.toggleFlowExpansion(flowId);
  }

  triggerFlowAction(flow: Flow, event: FlowMenuAction) {
    if (event === FlowMenuAction.DUPLICATE) {
      this.flowFacade.selectFlow(flow.name, flow.args);
      window.scrollTo({top: 0, behavior: 'smooth'});
    } else if (event === FlowMenuAction.CANCEL) {
      this.clientFacade.cancelFlow(flow.clientId, flow.flowId);
    }
  }

  entryTrackByFunction(index: number, entry: FlowListEntryWithDescriptor) {
    return entry.flow.flowId;
  }
}
