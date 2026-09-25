import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ViewChild,
  effect,
  inject,
  input,
} from '@angular/core';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

import {ListContainersFlowResult as ApiListContainersFlowResult} from '../../../lib/api/api_interfaces';
import {translateContainerDetails} from '../../../lib/api/translation/flow';
import {ContainerDetails} from '../../../lib/models/flow';
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

function containerDetailsFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly ContainerDetails[] {
  return collectionResults
    .map((result) => (result.payload as ApiListContainersFlowResult).containers)
    .flat()
    .filter((container) => container !== undefined)
    .map(translateContainerDetails);
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
  readonly collectionResults = input.required<
    readonly ContainerDetails[],
    readonly CollectionResult[]
  >({
    transform: containerDetailsFromCollectionResults,
  });

  protected readonly dataSource = new MatTableDataSource<ContainerDetails>();
  protected readonly displayedColumns = COLUMNS;

  constructor() {
    effect(() => {
      if (this.collectionResults().length > 0) {
        this.dataSource.data = this.collectionResults().slice();
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
