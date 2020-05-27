import {ChangeDetectionStrategy, Component, OnDestroy, OnInit} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {Subject} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {ClientPageFacade} from '../../store/client_page_facade';

/**
 * Component displaying the details and actions for a single Client.
 */
@Component({
  templateUrl: './client.ng.html',
  styleUrls: ['./client.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Client implements OnInit, OnDestroy {
  private readonly id$ = this.route.paramMap.pipe(
      map(params => params.get('id')),
      filter((id): id is string => id !== null));

  readonly client$ = this.clientPageFacade.selectedClient$;

  private readonly unsubscribe$ = new Subject<void>();

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageFacade: ClientPageFacade,
  ) {}

  ngOnInit() {
    this.id$.pipe(takeUntil(this.unsubscribe$)).subscribe(id => {
      this.clientPageFacade.selectClient(id);
    });
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
