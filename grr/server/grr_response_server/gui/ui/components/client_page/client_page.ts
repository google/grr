import {AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {MatDrawer} from '@angular/material/sidenav';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute, Router} from '@angular/router';
import {Subject} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {isNonNull} from '../../lib/preconditions';
import {ClientPageFacade} from '../../store/client_page_facade';
import {UserFacade} from '../../store/user_facade';
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
export class ClientPage implements OnInit, AfterViewInit, OnDestroy {
  static readonly CLIENT_DETAILS_ROUTE = 'details';

  readonly id$ = this.route.paramMap.pipe(
      map(params => params.get('id')),
      filter(isNonNull),
  );

  readonly client$ = this.clientPageFacade.selectedClient$;

  readonly currentUser$ = this.userFacade.currentUser$.pipe(
      map(user => user.name),
  );

  private readonly unsubscribe$ = new Subject<void>();

  @ViewChild('clientDetailsDrawer') clientDetailsDrawer!: MatDrawer;

  @ViewChild(Approval, {read: ElementRef}) approvalViewContainer?: ElementRef;

  approvalHeight: number = 0;

  readonly showApprovalView$ = this.clientPageFacade.approvalsEnabled$;

  private readonly resizeObserver = new ResizeObserver(() => {
    this.approvalHeight =
        this.approvalViewContainer?.nativeElement.offsetHeight ?? 0;
    this.changeDetectorRef.markForCheck();
  });

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageFacade: ClientPageFacade,
      private readonly userFacade: UserFacade,
      private readonly title: Title,
      private readonly changeDetectorRef: ChangeDetectorRef,
      private readonly router: Router,
  ) {}

  ngOnInit() {
    this.id$.pipe(takeUntil(this.unsubscribe$)).subscribe(id => {
      this.clientPageFacade.selectClient(id);
    });

    this.client$
        .pipe(
            takeUntil(this.unsubscribe$),
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

    const urlTokens = this.router.routerState.snapshot.url.split('/');
    if (urlTokens[urlTokens.length - 1] === ClientPage.CLIENT_DETAILS_ROUTE) {
      this.clientDetailsDrawer.open();
    }

    this.clientDetailsDrawer.openedStart.subscribe(() => {
      this.router.navigate(['details'], {relativeTo: this.route});
    });

    this.clientDetailsDrawer.closedStart.subscribe(() => {
      this.router.navigate(['.'], {relativeTo: this.route});
    });
  }

  onClientDetailsButtonClick() {
    this.clientDetailsDrawer.toggle();
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
