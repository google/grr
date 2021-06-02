import {ChangeDetectionStrategy, Component} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {combineLatest, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {Flow, FlowDescriptor, FlowDescriptorMap} from '../../lib/models/flow';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {FlowResultsLocalStore} from '../../store/flow_results_local_store';
import {FlowArgsDialog, FlowArgsDialogData} from '../flow_args_dialog/flow_args_dialog';
import {FlowMenuAction} from '../flow_details/flow_details';



interface FlowWithDescriptor {
  readonly flow: Flow;
  readonly descriptor?: FlowDescriptor;
}

/** Adds the corresponding FlowDescriptor to a Flow, if existent. */
function withDescriptor(fds: FlowDescriptorMap):
    ((flow: Flow) => FlowWithDescriptor) {
  return flow => ({
           flow,
           descriptor: fds.get(flow.name),
         });
}

/** Component that displays executed Flows on the currently selected Client. */
@Component({
  selector: 'flow-list',
  templateUrl: './flow_list.ng.html',
  styleUrls: ['./flow_list.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FlowResultsLocalStore],
})
export class FlowList {
  readonly entries$: Observable<ReadonlyArray<FlowWithDescriptor>> =
      combineLatest([
        this.clientPageGlobalStore.flowListEntries$,
        this.configGlobalStore.flowDescriptors$,
      ]).pipe(map(([flows, fds]) => flows.map(withDescriptor(fds))));

  constructor(
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly dialog: MatDialog,
  ) {}

  triggerFlowAction(entry: FlowWithDescriptor, event: FlowMenuAction) {
    if (event === FlowMenuAction.DUPLICATE) {
      this.clientPageGlobalStore.startFlowConfiguration(
          entry.flow.name, entry.flow.args);
      window.scrollTo({top: 0, behavior: 'smooth'});
    } else if (event === FlowMenuAction.CANCEL) {
      this.clientPageGlobalStore.cancelFlow(entry.flow.flowId);
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

  entryTrackByFunction(index: number, entry: FlowWithDescriptor) {
    return entry.flow.flowId;
  }
}
