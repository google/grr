import {Location} from '@angular/common';
import {ChangeDetectionStrategy, Component, OnDestroy, OnInit, QueryList, ViewChild, ViewChildren} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {MatDrawer} from '@angular/material/sidenav';
import {MatSnackBar} from '@angular/material/snack-bar';
import {ActivatedRoute, Router} from '@angular/router';
import {ClientLabel} from '@app/lib/models/client';
import {Subject} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

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

  @ViewChild('clientDetailsDrawer') clientDetailsDrawers!: MatDrawer;

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageFacade: ClientPageFacade,
      private readonly dialog: MatDialog,
      private readonly snackBar: MatSnackBar,
      private readonly location: Location,
      private readonly router: Router,
  ) {}

  ngOnInit() {
    this.id$.pipe(takeUntil(this.unsubscribe$)).subscribe(id => {
      this.clientPageFacade.selectClient(id);
    });

    this.clientPageFacade.removedClientLabels$
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(label => {
          this.showLabelRemovedSnackBar(label);
        }, err => {/* Nothing for now */});
  }

  ngAfterViewInit() {
    this.clientDetailsDrawers.closedStart.subscribe(() => {
      const urlTokens = this.location.path().split('/');
      this.location.go(urlTokens.slice(0, -1).join('/'));
    });

    this.location.onUrlChange(url => {
      const urlTokens = url.split('/');
      if (urlTokens[urlTokens.length - 1] === 'details') {
        this.clientDetailsDrawers.open();
      }
    });

    this.route.url.pipe(map(url => url[url.length - 1]))
        .subscribe(urlSegment => {
          if (urlSegment.path === 'details') {
            this.clientDetailsDrawers.open();
          }
        });
  }

  onClientDetailsButtonClick() {
    if (this.clientDetailsDrawers.opened) {
      this.clientDetailsDrawers.close();
    } else {
      const currentUrl = this.location.path();
      this.location.go(`${currentUrl}/details`);
    }
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
          duration: Client.LABEL_REMOVED_SNACKBAR_DURATION_MS,
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

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
