import {ChangeDetectionStrategy, Component, OnDestroy, OnInit} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute} from '@angular/router';
import {Subject} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {ClientLabel} from '../../lib/models/client';
import {isNonNull} from '../../lib/preconditions';
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
      filter(isNonNull),
  );

  readonly client$ = this.clientPageFacade.selectedClient$;

  private readonly unsubscribe$ = new Subject<void>();

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageFacade: ClientPageFacade,
      private readonly title: Title,
  ) {}

  trackLabel(index: number, label: ClientLabel) {
    return label.name;
  }

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

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
