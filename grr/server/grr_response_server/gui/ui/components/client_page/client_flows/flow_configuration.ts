import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input as routerInput,
} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {Title} from '@angular/platform-browser';

import {Flow} from '../../../lib/models/flow';
import {ClientStore} from '../../../store/client_store';
import {FlowArgsForm} from '../../shared/flow_args_form/flow_args_form';
import {User} from '../../shared/user';
/**
 * Component displaying flow configuration of a single flow.
 */
@Component({
  selector: 'flow-configuration',
  templateUrl: './flow_configuration.ng.html',
  styleUrls: ['./flow_configuration.scss'],
  imports: [CommonModule, FlowArgsForm, User, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowConfiguration {
  readonly clientStore = inject(ClientStore);

  flowId = routerInput<string | undefined>();

  flow = computed<Flow | undefined>(() => {
    const flowId = this.flowId();
    if (flowId) {
      return this.clientStore.flowsByFlowId().get(flowId);
    }
    return undefined;
  });

  constructor() {
    inject(Title).setTitle('GRR | Client > Flow > Configuration');
  }
}
