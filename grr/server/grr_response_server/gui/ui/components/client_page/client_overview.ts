import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialog} from '@angular/material/dialog';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';

import {ClientLabel, User} from '../../lib/models/client';
import {ClientStore} from '../../store/client_store';
import {GlobalStore} from '../../store/global_store';
import {ApprovalChip} from '../shared/approval_chip';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleState,
  CollapsibleTitle,
} from '../shared/collapsible_container';
import {CopyButton} from '../shared/copy_button';
import {ErrorMessage} from '../shared/error_message';
import {OnlineChip} from '../shared/online_chip';
import {Timestamp} from '../shared/timestamp';
import {
  ClientAddLabelDialog,
  ClientAddLabelDialogData,
} from './client_add_label_dialog';
import {
  ClientRemoveLabelDialog,
  ClientRemoveLabelDialogData,
} from './client_remove_label_dialog';

/**
 * Component displaying overview info of a Client.
 */
@Component({
  selector: 'client-overview',
  templateUrl: './client_overview.ng.html',
  styleUrls: ['./client_overview.scss'],
  imports: [
    CollapsibleContainer,
    CollapsibleContent,
    CollapsibleTitle,
    CommonModule,
    CopyButton,
    ErrorMessage,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    RouterModule,
    Timestamp,
    MatTooltipModule,
    OnlineChip,
    ApprovalChip,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientOverview {
  readonly clientStore = inject(ClientStore);
  readonly globalStore = inject(GlobalStore);
  private readonly dialog = inject(MatDialog);

  protected readonly CollapsibleState = CollapsibleState;

  protected expanded = true;

  protected readonly clientWarnings = computed<string[]>(() => {
    const client = this.clientStore.client();
    if (!client) return [];
    const clientLabels = client.labels.map((label) => label.name) ?? [];
    const warnings = this.globalStore.uiConfig()?.clientWarnings?.rules ?? [];
    return warnings
      .filter((warning) => {
        return warning.withLabels?.some((label) =>
          clientLabels.includes(label),
        );
      })
      .map((warning) => warning.message ?? '');
  });

  constructor() {
    // TODO: Move this to a more appropriate place.
    this.globalStore.fetchAllLabels();
  }

  formatUsers(users: readonly User[]) {
    if (!users || !users.length) {
      return '(None)';
    }
    return users.map((user) => user.username).join(', ');
  }

  openAddLabelDialog() {
    const dialogData: ClientAddLabelDialogData = {
      clientLabels: this.clientStore.client()?.labels ?? [],
      allLabels: this.globalStore.allLabels() ?? [],
      onAddLabel: (label: string) => {
        this.clientStore.addClientLabel(label);
        // In theory this this call is only needed when the label is new, but
        // we do not check here if the label is new as the call to fetch all
        // labels is cheap.
        this.globalStore.fetchAllLabels();
      },
    };
    this.dialog.open(ClientAddLabelDialog, {data: dialogData});
  }

  openRemoveLabelDialog(label: ClientLabel) {
    const dialogData: ClientRemoveLabelDialogData = {
      label,
      onRemoveLabel: () => {
        this.clientStore.removeClientLabel(label.name);
      },
    };
    this.dialog.open(ClientRemoveLabelDialog, {data: dialogData});
  }
}
