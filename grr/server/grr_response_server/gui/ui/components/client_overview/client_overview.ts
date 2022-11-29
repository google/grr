import {ChangeDetectionStrategy, Component, Input, OnDestroy, OnInit} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {MatSnackBar} from '@angular/material/snack-bar';
import {combineLatest, firstValueFrom} from 'rxjs';
import {filter, map, takeUntil, withLatestFrom} from 'rxjs/operators';

import {OnlineNotificationArgs} from '../../lib/api/api_interfaces';
import {ClientLabel, isClientOnline, User} from '../../lib/models/client';
import {FlowState} from '../../lib/models/flow';
import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {UserGlobalStore} from '../../store/user_global_store';
import {ClientAddLabelDialog} from '../client_add_label_dialog/client_add_label_dialog';

/**
 * Component displaying overview info of a Client.
 */
@Component({
  selector: 'client-overview',
  templateUrl: './client_overview.ng.html',
  styleUrls: ['./client_overview.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientOverview implements OnInit, OnDestroy {
  private static readonly LABEL_REMOVED_SNACKBAR_DURATION_MS = 4000;

  readonly client$ = this.clientPageGlobalStore.selectedClient$;

  readonly showApprovalChip$ = this.clientPageGlobalStore.approvalsEnabled$;

  readonly approval$ = this.clientPageGlobalStore.latestApproval$;

  readonly hasAccess$ = this.clientPageGlobalStore.hasAccess$;

  readonly ngOnDestroy = observeOnDestroy(this);

  readonly showOnlineNotificationToggle$ =
      combineLatest([this.client$, this.hasAccess$])
          .pipe(
              map(([client, hasAccess]) => hasAccess &&
                      (!client?.lastSeenAt ||
                       !isClientOnline(client.lastSeenAt))),
          );

  readonly activeOnlineNotificationArgs$ =
      this.clientPageGlobalStore.flowListEntries$.pipe(
          withLatestFrom(this.userGlobalStore.currentUser$),
          map(([data, user]) => data.flows?.find(
                  f => f.name === 'OnlineNotification' &&
                      f.creator === user.name &&
                      f.state === FlowState.RUNNING)),
          map(flow => flow?.args as OnlineNotificationArgs | undefined),
      );

  @Input() collapsed: boolean = false;

  constructor(
      private readonly userGlobalStore: UserGlobalStore,
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly dialog: MatDialog,
      private readonly snackBar: MatSnackBar,
  ) {}

  ngOnInit() {
    this.clientPageGlobalStore.lastRemovedClientLabel$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(isNonNull),
            )
        .subscribe(label => {
          this.showLabelRemovedSnackBar(label);
        });
  }

  labelsTrackByName(index: number, item: ClientLabel): string {
    return item.name;
  }

  openAddLabelDialog(clientLabels: ReadonlyArray<ClientLabel>) {
    const addLabelDialog = this.dialog.open(ClientAddLabelDialog, {
      data: clientLabels,
    });

    addLabelDialog.afterClosed().subscribe(newLabel => {
      if (newLabel !== undefined && newLabel !== null && newLabel !== '') {
        this.addLabel(newLabel);
      }
    });
  }

  private showLabelRemovedSnackBar(label: string) {
    this.snackBar
        .open(`Label "${label}" removed`, 'UNDO', {
          duration: ClientOverview.LABEL_REMOVED_SNACKBAR_DURATION_MS,
          verticalPosition: 'top'
        })
        .afterDismissed()
        .subscribe(snackBar => {
          if (snackBar.dismissedByAction) {
            this.addLabel(label);
          }
        });
  }

  removeLabel(label: string) {
    this.clientPageGlobalStore.removeClientLabel(label);
  }

  addLabel(label: string) {
    this.clientPageGlobalStore.addClientLabel(label);
  }

  formatUsers(users: ReadonlyArray<User>) {
    if (!users || !users.length) {
      return '(None)';
    }
    return users.map(user => user.username).join(', ');
  }

  async triggerOnlineNotification() {
    this.clientPageGlobalStore.startFlowConfiguration('OnlineNotification');
    const flowDescriptor = await firstValueFrom(
        this.clientPageGlobalStore.selectedFlowDescriptor$.pipe(
            filter(isNonNull)));
    this.clientPageGlobalStore.startFlow(flowDescriptor.defaultArgs);
  }
}
