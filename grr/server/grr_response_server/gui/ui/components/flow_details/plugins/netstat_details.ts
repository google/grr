import {ChangeDetectionStrategy, Component, OnDestroy, ViewChild} from '@angular/core';
import {MatSort} from '@angular/material/sort';
import {MatTableDataSource} from '@angular/material/table';
import {Observable} from 'rxjs';
import {map, takeUntil} from 'rxjs/operators';

import {NetstatArgs, NetworkConnection} from '../../../lib/api/api_interfaces';
import {observeOnDestroy} from '../../../lib/reactive';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {Plugin} from './plugin';

const INITIAL_RESULT_COUNT = 1000;

const COLUMNS: ReadonlyArray<string> = [
  'pid',
  'processName',
  'state',
  'type',
  'family',
  'localIP',
  'localPort',
  'remoteIP',
  'remotePort',
];

interface ConnectionRow extends NetworkConnection {
  readonly localIP?: string;
  readonly localPort?: number;
  readonly remoteIP?: string;
  readonly remotePort?: number;
}

function asConnectionRow(connection: NetworkConnection): ConnectionRow {
  return {
    ...connection,
    localIP: connection.localAddress?.ip,
    localPort: connection.localAddress?.port,
    remoteIP: connection.remoteAddress?.ip,
    remotePort: connection.remoteAddress?.port,
  };
}

/**
 * Component that displays the details (results) for a
 * particular Netstat Flow.
 */
@Component({
  selector: 'netstat-details',
  templateUrl: './netstat_details.ng.html',
  styleUrls: ['./netstat_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NetstatDetails extends Plugin implements OnDestroy {
  readonly displayedColumns = COLUMNS;

  @ViewChild(MatSort) sort!: MatSort;

  readonly dataSource = new MatTableDataSource<ConnectionRow>();

  readonly netstatResults$: Observable<ReadonlyArray<ConnectionRow>> =
      this.flowResultsLocalStore.results$.pipe(
          map(results =>
                  results?.map((data) => data.payload as NetworkConnection)),
          map(connections =>
                  connections?.map(connection => asConnectionRow(connection))),
      );

  override readonly ngOnDestroy = observeOnDestroy(this);

  constructor(
      private readonly flowResultsLocalStore: FlowResultsLocalStore,
  ) {
    super();
    this.flowResultsLocalStore.query(
        this.flow$.pipe(map(flow => ({flow, withType: 'NetworkConnection'}))));

    this.netstatResults$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(results => {
          this.dataSource.data = results as ConnectionRow[];
        });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
  }

  private readonly flowArgs$ =
      this.flow$.pipe(map(flow => flow.args as NetstatArgs));
  readonly title$ = this.flowArgs$.pipe(map(args => {
    if (args.listeningOnly) {
      return 'Listening only';
    } else {
      return 'All connections';
    }
  }));

  onShowClicked() {
    this.flowResultsLocalStore.queryMore(INITIAL_RESULT_COUNT);
  }

  trackByConnectionRowIndex(index: number, item: ConnectionRow) {
    return index;
  }
}
