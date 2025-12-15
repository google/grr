import {Clipboard, ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatBadgeModule} from '@angular/material/badge';
import {MatButtonModule} from '@angular/material/button';
import {MatDialog, MatDialogConfig} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
import {MatMenuModule} from '@angular/material/menu';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Router, RouterModule} from '@angular/router';

import {
  Flow,
  FlowState,
  FlowType,
  ScheduledFlow,
} from '../../../lib/models/flow';
import {makeFlowLink} from '../../../lib/routing';
import {checkExhaustive} from '../../../lib/utils';
import {FlowArgsPreviewPipe} from '../../../pipes/flow_pipes/flow_args_preview_pipe';
import {FriendlyFlowNamePipe} from '../../../pipes/flow_pipes/friendly_flow_name';
import {ClientStore} from '../../../store/client_store';
import {GlobalStore} from '../../../store/global_store';
import {CopyButton} from '../../shared/copy_button';
import {FlowStateIcon} from '../../shared/flow_state_icon';
import {SplitPanel} from '../../shared/split_panel/split_panel';
import {Timestamp} from '../../shared/timestamp';
import {User} from '../../shared/user';
import {CreateFlowDialog, CreateFlowDialogData} from './create_flow_dialog';

/** Flow filter enum used for classifying the flows. */
export enum FlowFilter {
  ALL_HUMAN_FLOWS = 'All human flows',
  ALL_ROBOT_FLOWS = 'All robot flows',
  ALL_FLOWS = 'All flows',
}

const INITIAL_FLOW_FILTER = FlowFilter.ALL_HUMAN_FLOWS;

/**
 * Component displaying the flows of a Client.
 */
@Component({
  selector: 'client-flows',
  templateUrl: './client_flows.ng.html',
  styleUrls: ['./client_flows.scss'],
  imports: [
    CommonModule,
    CopyButton,
    ClipboardModule,
    FlowArgsPreviewPipe,
    FlowStateIcon,
    FormsModule,
    FriendlyFlowNamePipe,
    MatBadgeModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatListModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTooltipModule,
    ReactiveFormsModule,
    RouterModule,
    SplitPanel,
    Timestamp,
    User,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientFlows {
  protected readonly clientStore = inject(ClientStore);
  protected readonly globalStore = inject(GlobalStore);
  private readonly router = inject(Router);
  protected readonly clipboard = inject(Clipboard);
  private readonly dialog = inject(MatDialog);

  protected readonly FlowState = FlowState;
  protected readonly FlowFilter = FlowFilter;

  protected expandedNestedFlows = new Set<string>();

  readonly flowFiltersForm = new FormControl(INITIAL_FLOW_FILTER);
  protected readonly flowFilter = toSignal(this.flowFiltersForm.valueChanges, {
    // Set the initial value explicitly as the toObservable function that is
    // used under the hood emits initially `undefined`.
    initialValue: INITIAL_FLOW_FILTER,
  });
  protected readonly filteredFlows = computed(() => {
    return this.clientStore.flows().filter((entry) => {
      const flowFilter = this.flowFilter();
      if (!flowFilter) {
        return false;
      }
      switch (flowFilter) {
        case FlowFilter.ALL_HUMAN_FLOWS:
          return entry.isRobot === false;
        case FlowFilter.ALL_ROBOT_FLOWS:
          return entry.isRobot === true;
        case FlowFilter.ALL_FLOWS:
          return true;
        default:
          checkExhaustive(flowFilter);
      }
    });
  });

  constructor() {
    const initialNavigation = effect(() => {
      if (!this.router.url.endsWith('flows')) {
        initialNavigation.destroy();
        return;
      }
      const filteredFlows = this.filteredFlows();
      if (filteredFlows.length > 0) {
        this.router.navigate([
          'clients',
          this.clientStore.clientId(),
          'flows',
          filteredFlows[0].flowId,
        ]);

        initialNavigation.destroy();
      }
    });
  }

  protected openCreateFlowDialog(flowType?: FlowType, flowArgs?: object) {
    const dialogData: CreateFlowDialogData = {
      flowType,
      flowArgs,
      onSubmit: (
        flowName: string,
        flowArgs: object,
        disableRrgSupport: boolean,
      ) => {
        this.clientStore.scheduleOrStartFlow(
          flowName,
          flowArgs,
          disableRrgSupport,
        );
        // Close the dialog after the flow form is submitted.
        dialogRef.close();
      },
      client: this.clientStore.client()!,
    };
    const dialogConfig = new MatDialogConfig();
    dialogConfig.data = dialogData;
    dialogConfig.minWidth = '60vw';
    dialogConfig.height = '70vh';
    dialogConfig.autoFocus = false;

    const dialogRef = this.dialog.open(CreateFlowDialog, dialogConfig);
  }

  protected copyFlowLink(event: MouseEvent, flow: Flow) {
    event.stopPropagation();
    event.preventDefault();
    this.clipboard.copy(makeFlowLink(flow.clientId, flow.flowId));
  }

  protected copyScheduledFlowLink(
    event: MouseEvent,
    scheduledFlow: ScheduledFlow,
  ) {
    event.stopPropagation();
    event.preventDefault();
    this.clipboard.copy(
      makeFlowLink(scheduledFlow.clientId, scheduledFlow.scheduledFlowId),
    );
  }

  protected copyToClipboard(content: string) {
    this.clipboard.copy(content);
  }

  protected duplicateFlow(flow: Flow) {
    this.openCreateFlowDialog(flow.flowType, flow.args as object);
  }

  protected createHunt(flow: Flow) {
    this.router.navigate(['/new-hunt'], {
      queryParams: {
        'clientId': flow.clientId,
        'flowId': flow.flowId,
      },
    });
  }

  protected createFleetCollection(flow: Flow) {
    this.router.navigate(['/new-fleet-collection'], {
      queryParams: {
        'clientId': flow.clientId,
        'flowId': flow.flowId,
      },
    });
  }

  protected toggleNestedFlows(event: MouseEvent, flowId: string) {
    // Toggling the nested flows should not navigate to this flow.
    event.preventDefault();
    event.stopPropagation();
    if (this.expandedNestedFlows.has(flowId)) {
      this.expandedNestedFlows.delete(flowId);
    } else {
      this.expandedNestedFlows.add(flowId);
    }
  }

  /**
   * API Request to start a given flow.
   */
  getCreateFlowAPIRequest(flow: Flow) {
    return this.createFlowApiRequestStr(flow);
  }

  /** API request to start a given flow. */
  createFlowApiRequestStr(flow: Flow) {
    return `CSRFTOKEN='curl ${window.location.origin} -o /dev/null -s -c - | grep csrftoken  | cut -f 7' \\
  curl -X POST -H "Content-Type: application/json" -H "X-CSRFToken: $CSRFTOKEN" \\
  ${window.location.origin}/api/v2/clients/${flow.clientId}/flows -d @- << EOF
${JSON.stringify({flow: {args: flow.args, name: flow.name}}, null, 2)}
EOF`;
  }
}
