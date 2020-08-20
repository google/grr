import {ChangeDetectionStrategy, Component, OnDestroy, OnInit} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {MatSnackBar} from '@angular/material/snack-bar';
import {ActivatedRoute} from '@angular/router';
import {ClientLabel} from '@app/lib/models/client';
import {Subject} from 'rxjs';
import {filter, map, takeUntil, takeWhile, take} from 'rxjs/operators';

import {ClientPageFacade} from '../../store/client_page_facade';
import {ClientAddLabelDialog} from '../client_add_label_dialog/client_add_label_dialog';

/**
 * Component displaying the details and actions for a single Client.
 */
@Component({
  templateUrl: './client.ng.html',
  styleUrls: ['./client.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Client implements OnInit, OnDestroy {
  private static LABEL_REMOVED_SNACKBAR_DURATION_MS = 4000;
  private readonly id$ = this.route.paramMap.pipe(
      map(params => params.get('id')),
      filter((id): id is string => id !== null));

  readonly client$ = this.clientPageFacade.selectedClient$;

  private readonly unsubscribe$ = new Subject<void>();

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageFacade: ClientPageFacade,
      private readonly dialog: MatDialog,
      private readonly snackBar: MatSnackBar,
  ) {}

  ngOnInit() {
    this.id$.pipe(takeUntil(this.unsubscribe$)).subscribe(id => {
      this.clientPageFacade.selectClient(id);
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
        .open(
            `Label "${label}" removed`, 'UNDO',
            {duration: Client.LABEL_REMOVED_SNACKBAR_DURATION_MS, verticalPosition: 'top'})
        .afterDismissed()
        .subscribe(snackBar => {
          if (snackBar.dismissedByAction) {
            this.addLabel(label);
          }
        });
  }

  removeLabel(label: string) {
    this.clientPageFacade.removeClientLabel(label);
    this.clientPageFacade.removeClientLabelState$.pipe(
      filter(state => state.state === 'error' || state.state === 'success'),
      take(1),
    ).subscribe((state) => {
      if (state.state === 'success') {
        this.showLabelRemovedSnackBar(label);
      }
      this.clientPageFacade.clearRemoveClientLabelState();
    });
  }

  addLabel(label: string) {
    this.clientPageFacade.addClientLabel(label);
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
