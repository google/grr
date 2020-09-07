import {ChangeDetectionStrategy, Component, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {Subject} from 'rxjs';
import {filter, map, take, takeUntil} from 'rxjs/operators';

import {ClientPageFacade} from '../../store/client_page_facade';
import {ClientOverview} from '../client_overview/client_overview';

/**
 * Component displaying the details and actions for a single Client.
 */
@Component({
  templateUrl: './client.ng.html',
  styleUrls: ['./client.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Client implements OnInit, OnDestroy {
  static readonly CLIENT_DETAILS_ROUTE = 'details';

  private readonly id$ = this.route.paramMap.pipe(
      map(params => params.get('id')),
      filter((id): id is string => id !== null));

  readonly client$ = this.clientPageFacade.selectedClient$;

  private readonly unsubscribe$ = new Subject<void>();

  @ViewChild(ClientOverview) clientOverview!: ClientOverview;

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageFacade: ClientPageFacade,
      private readonly router: Router,
  ) {}

  ngOnInit() {
    this.id$.pipe(takeUntil(this.unsubscribe$)).subscribe(id => {
      this.clientPageFacade.selectClient(id);
    });
  }

  ngAfterViewInit() {
    const urlTokens = this.router.routerState.snapshot.url.split('/');
    if (urlTokens[urlTokens.length - 1] === Client.CLIENT_DETAILS_ROUTE) {
      this.clientOverview.openClientDetailsDrawer();
    }

    this.clientOverview.clientDetailsDrawerOpening$.subscribe(() => {
      this.router.navigate(['details'], {relativeTo: this.route});
    });

    this.clientOverview.clientDetailsDrawerClosing$.subscribe(() => {
      this.router.navigate(['.'], {relativeTo: this.route});
    });
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
