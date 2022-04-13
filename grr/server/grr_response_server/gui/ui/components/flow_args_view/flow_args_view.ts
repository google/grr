import {Component, Input} from '@angular/core';

import {FlowDescriptor} from '../../lib/models/flow';

/** Flow descriptor and args to display. */
export interface FlowArgsViewData {
  readonly flowDescriptor: FlowDescriptor;
  readonly flowArgs: unknown;
}

/** Form that displays flow arguments. */
@Component({
  selector: 'app-flow-args-view',
  templateUrl: './flow_args_view.ng.html',
  styleUrls: ['./flow_args_view.scss'],
})
export class FlowArgsView {
  flowDescriptor: FlowDescriptor|null = null;

  @Input()
  set flowArgsViewData(data: FlowArgsViewData|null) {
    if (!data) {
      this.flowDescriptor = null;
    } else {
      this.flowDescriptor = {
        ...data.flowDescriptor,
        defaultArgs: data.flowArgs,
      };
    }
  }
}
