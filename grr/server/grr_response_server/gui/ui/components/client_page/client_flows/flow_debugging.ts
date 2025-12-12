import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input as routerInput,
} from '@angular/core';
import {Title} from '@angular/platform-browser';

import {ClientStore} from '../../../store/client_store';
import {FlowStore} from '../../../store/flow_store';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleTitle,
} from '../../shared/collapsible_container';
import {FlowLogs} from './flow_logs';
import {FlowOutputPluginLogs} from './flow_output_plugin_logs';

/**
 * Component displaying debugging information about a flow.
 */
@Component({
  selector: 'flow-debugging',
  templateUrl: './flow_debugging.ng.html',
  styleUrls: ['./flow_debugging.scss'],
  imports: [
    CollapsibleContainer,
    CollapsibleContent,
    CollapsibleTitle,
    CommonModule,
    FlowLogs,
    FlowOutputPluginLogs,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowDebugging {
  protected readonly clientStore = inject(ClientStore);
  protected readonly flowStore = inject(FlowStore);

  flowId = routerInput<string | undefined>();

  protected stringify(data: unknown) {
    return JSON.stringify(data, null, 2);
  }

  constructor() {
    inject(Title).setTitle('GRR | Client > Flow > Debugging');
  }
}
