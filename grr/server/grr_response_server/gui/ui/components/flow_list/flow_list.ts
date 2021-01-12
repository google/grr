import {ChangeDetectionStrategy, Component} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {combineLatest, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {FlowDescriptor, FlowDescriptorMap, FlowListEntry, FlowResultsQuery} from '../../lib/models/flow';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';
import {FlowArgsDialog, FlowArgsDialogData} from '../flow_args_dialog/flow_args_dialog';
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
      private readonly dialog: MatDialog,
  ) {}

  queryFlowResults(flowId: string, query: FlowResultsQuery) {
    this.clientPageFacade.queryFlowResults(query);
  }

  triggerFlowAction(entry: FlowListEntryWithDescriptor, event: FlowMenuAction) {
    if (event === FlowMenuAction.DUPLICATE) {
      this.clientPageFacade.startFlowConfiguration(
          entry.flow.name, entry.flow.args);
      window.scrollTo({top: 0, behavior: 'smooth'});
    } else if (event === FlowMenuAction.CANCEL) {
      this.clientPageFacade.cancelFlow(entry.flow.flowId);
    } else if (event === FlowMenuAction.VIEW_ARGS) {
      if (!entry.descriptor) {
        throw new Error('Cannot show flow args without flow descriptor.');
      }
      const data: FlowArgsDialogData = {
        flowArgs: entry.flow.args as {},
        flowDescriptor: entry.descriptor,
      };
      this.dialog.open(FlowArgsDialog, {data});
    }
  }

  entryTrackByFunction(index: number, entry: FlowListEntryWithDescriptor) {
    return entry.flow.flowId;
  }
}
