import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  signal,
  ViewChild,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {MatChipsModule} from '@angular/material/chips';
import {MatDividerModule} from '@angular/material/divider';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute, RouterModule} from '@angular/router';

import {Client} from '../../lib/models/client';
import {ClientSearchStore} from '../../store/client_search_store';
import {RecentClientApproval} from '../shared/approvals/recent_client_approval';
import {CopyButton} from '../shared/copy_button';
import {FilterPaginate} from '../shared/filter_paginate';
import {OnlineChip} from '../shared/online_chip';
import {Timestamp} from '../shared/timestamp';
import {SearchBox} from './search_box';

/**
 * Component displaying the client search results.
 */
@Component({
  templateUrl: './client_search.ng.html',
  styleUrls: ['./client_search.scss'],
  imports: [
    CommonModule,
    CopyButton,
    FilterPaginate,
    MatChipsModule,
    MatDividerModule,
    MatSortModule,
    MatTableModule,
    MatTooltipModule,
    OnlineChip,
    RouterModule,
    RecentClientApproval,
    SearchBox,
    Timestamp,
  ],
  providers: [ClientSearchStore],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientSearch implements AfterViewInit {
  protected readonly clientSearchStore = inject(ClientSearchStore);
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  private readonly route = inject(ActivatedRoute);
  @ViewChild(MatSort) sort!: MatSort;

  readonly dataSource = new MatTableDataSource<Client>();

  private readonly queryParams = toSignal(this.route.queryParams);
  protected readonly approvalReason = signal<string | undefined>(undefined);

  protected readonly columns = [
    'clientId',
    'fqdn',
    'users',
    'labels',
    'online',
    'lastSeenAt',
  ];

  constructor() {
    inject(Title).setTitle('GRR | Client Search');

    effect(() => {
      this.approvalReason.set(this.queryParams()?.['reason'] ?? undefined);
    });

    effect(() => {
      this.dataSource.data = this.clientSearchStore.clients().slice();
    });
    this.clientSearchStore.fetchRecentClientApprovals();
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;

    this.dataSource.sortingDataAccessor = (item, property) => {
      if (property === 'clientId') {
        return item.clientId;
      }
      if (property === 'fqdn') {
        return item.knowledgeBase.fqdn ?? '';
      }
      if (property === 'lastSeenAt') {
        return item.lastSeenAt?.getTime() ?? 0;
      }
      return '';
    };

    this.dataSource.filterPredicate = (data: Client, filter: string) => {
      return (
        data.clientId.includes(filter) ||
        data.knowledgeBase.fqdn?.includes(filter) ||
        data.knowledgeBase.users?.some((user) =>
          user.username?.includes(filter),
        ) ||
        data.labels.some((label) => label.name.includes(filter)) ||
        data.lastSeenAt?.getTime().toString().includes(filter) ||
        data.lastSeenAt?.toUTCString().includes(filter) ||
        false
      );
    };
  }

  /** Announce the change in sort state for assistive technology. */
  protected announceSortChange(sortState: Sort) {
    if (sortState.direction) {
      this.liveAnnouncer.announce(`Sorted ${sortState.direction}`);
    } else {
      this.liveAnnouncer.announce('Sorting cleared');
    }
  }
}
