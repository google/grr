import {AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, OnDestroy, ViewChild} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute} from '@angular/router';
import {filter, map, takeUntil} from 'rxjs/operators';

import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {UserGlobalStore} from '../../store/user_global_store';
import {Approval} from '../approval/approval';

// Minimalistic polyfill for ResizeObserver typings. These typings represent a
// subset of the real interface, until TypeScript implements the real typings.
// See https://github.com/Microsoft/TypeScript/issues/28502.
declare class ResizeObserver {
  constructor(callback: () => void);
  observe: (target: Element) => void;
  unobserve: (target: Element) => void;
  disconnect: () => void;
}

declare global {
  interface Window {
    // tslint:disable-next-line:enforce-name-casing
    ResizeObserver: typeof ResizeObserver;
  }
}

/**
 * Component displaying the details and actions for a single Client.
 */
@Component({
  templateUrl: './client_page.ng.html',
  styleUrls: ['./client_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientPage implements AfterViewInit, OnDestroy {
  static readonly CLIENT_DETAILS_ROUTE = 'details';

  readonly id$ = this.route.paramMap.pipe(
      map(params => params.get('id')),
      filter(isNonNull),
  );

  readonly client$ = this.clientPageGlobalStore.selectedClient$;

  readonly currentUser$ = this.userGlobalStore.currentUser$.pipe(
      map(user => user.name),
  );

  readonly ngOnDestroy = observeOnDestroy();

  @ViewChild(Approval, {read: ElementRef}) approvalViewContainer?: ElementRef;

  approvalHeight: number = 0;

  readonly showApprovalView$ = this.clientPageGlobalStore.approvalsEnabled$;

  private readonly resizeObserver = new ResizeObserver(() => {
    this.approvalHeight =
        this.approvalViewContainer?.nativeElement.offsetHeight ?? 0;
    this.changeDetectorRef.markForCheck();
  });

  constructor(
      readonly route: ActivatedRoute,
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly selectedClientGlobalStore: SelectedClientGlobalStore,
      private readonly userGlobalStore: UserGlobalStore,
      private readonly title: Title,
      private readonly changeDetectorRef: ChangeDetectorRef,
  ) {
    this.selectedClientGlobalStore.selectClientId(
        this.route.paramMap.pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            map(params => params.get('id')),
            filter(isNonNull),
            ),
    );

    this.selectedClientGlobalStore.clientId$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(isNonNull),
            )
        .subscribe(id => {
          this.clientPageGlobalStore.selectClient(id);
        });

    this.client$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe(client => {
          const fqdn = client.knowledgeBase.fqdn;
          const info = fqdn ? `${fqdn} (${client.clientId})` : client.clientId;
          this.title.setTitle(`GRR | ${info}`);
        });
  }

  ngAfterViewInit() {
    if (this.approvalViewContainer !== undefined) {
      this.resizeObserver.observe(this.approvalViewContainer.nativeElement);
    }
  }
}
