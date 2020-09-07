import {ChangeDetectionStrategy, Component, Input, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {MatDrawer} from '@angular/material/sidenav';
import {MatSnackBar} from '@angular/material/snack-bar';
import {ClientAddLabelDialog} from '@app/components/client_add_label_dialog/client_add_label_dialog';
import {ClientLabel} from '@app/lib/models/client';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {Subject} from 'rxjs';
import {takeUntil} from 'rxjs/operators';

/**
 * Component displaying the details and actions for a single Client.
 */
@Component({
  selector: 'client-overview',
  templateUrl: './client_overview.ng.html',
  styleUrls: ['./client_overview.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientOverview implements OnInit, OnDestroy {
  private static LABEL_REMOVED_SNACKBAR_DURATION_MS = 4000;

  /**
   * Non-empty string to be appended to the URL when the client details opens.
   * Defaults to 'details'.
   */
  readonly client$ = this.clientPageFacade.selectedClient$;
  private readonly unsubscribe$ = new Subject<void>();
  @ViewChild('clientDetailsDrawer') clientDetailsDrawer!: MatDrawer;

  readonly clientDetailsDrawerOpening$ = new Subject<void>();
  readonly clientDetailsDrawerClosing$ = new Subject<void>();

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
      private readonly dialog: MatDialog,
      private readonly snackBar: MatSnackBar,
  ) {}

  ngOnInit() {
    this.clientPageFacade.lastRemovedClientLabel$
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(label => {
          this.showLabelRemovedSnackBar(label);
        });
  }

  ngAfterViewInit() {
    this.clientDetailsDrawer.openedStart.subscribe(() => {
      this.clientDetailsDrawerOpening$.next();
    });

    this.clientDetailsDrawer.closedStart.subscribe(() => {
      this.clientDetailsDrawerClosing$.next();
    });
  }

  labelsTrackByName(index: number, item: ClientLabel): string {
    return item.name;
  }

  onClientDetailsButtonClick() {
    this.clientDetailsDrawer.toggle();
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
    this.clientPageFacade.removeClientLabel(label);
  }

  addLabel(label: string) {
    this.clientPageFacade.addClientLabel(label);
  }

  openClientDetailsDrawer() {
    this.clientDetailsDrawer.open();
  }

  closeClientDetailsDrawer() {
    this.clientDetailsDrawer.close();
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
    this.clientDetailsDrawerOpening$.complete();
    this.clientDetailsDrawerClosing$.complete();
  }
}
