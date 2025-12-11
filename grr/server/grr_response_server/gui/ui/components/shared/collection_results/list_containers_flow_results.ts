import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ViewChild,
  computed,
  effect,
  inject,
  input,
} from '@angular/core';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

import {ListContainersFlowResult as ApiListContainersFlowResult} from '../../../lib/api/api_interfaces';
import {translateContainerDetails} from '../../../lib/api/translation/flow';
import {ContainerDetails} from '../../../lib/models/flow';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {FilterPaginate} from '../filter_paginate';
import {Timestamp} from '../timestamp';

const COLUMNS: readonly string[] = [
  'containerId',
  'imageName',
  'command',
  'createdAt',
  'status',
  'ports',
  'names',
  'localVolumes',
  'mounts',
  'networks',
];

const HUNT_COLUMNS: readonly string[] = ['clientId', ...COLUMNS];

interface ContainerDetailsWithClientId extends ContainerDetails {
  clientId: string;
}

function containerDetailsFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly ContainerDetailsWithClientId[] {
  return collectionResults
    .map((result) => {
      const containers = (result.payload as ApiListContainersFlowResult)
        .containers;

      const containerDetails: ContainerDetailsWithClientId[] = [];
      for (const container of containers ?? []) {
        if (!container) {
          continue;
        }
        containerDetails.push({
          ...translateContainerDetails(container),
          clientId: result.clientId,
        });
      }
      return containerDetails;
    })
    .flat();
}

/**
 * Component that displays `ListContainerFlowResult` flow results.
 */
@Component({
  selector: 'list-containers-flow-results',
  templateUrl: './list_containers_flow_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [
    CommonModule,
    CopyButton,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
    Timestamp,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListContainersFlowResults implements AfterViewInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  readonly containerDetails = computed(() =>
    containerDetailsFromCollectionResults(this.collectionResults()),
  );

  protected readonly dataSource = new MatTableDataSource<ContainerDetails>();

  protected readonly displayedColumns = computed(() => {
    if (this.collectionResults().some(isHuntResult)) {
      return HUNT_COLUMNS;
    }
    return COLUMNS;
  });

  constructor() {
    effect(() => {
      if (this.containerDetails().length > 0) {
        this.dataSource.data = this.containerDetails().slice();
      }
    });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
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
