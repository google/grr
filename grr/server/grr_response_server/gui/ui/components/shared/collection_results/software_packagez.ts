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
import {SoftwarePackages as ApiSoftwarePackages} from '../../../lib/api/api_interfaces';
import {translateSoftwarePackage} from '../../../lib/api/translation/flow';
import {SoftwarePackage} from '../../../lib/models/flow';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {FilterPaginate} from '../filter_paginate';
import {Timestamp} from '../timestamp';

const COLUMNS: readonly string[] = [
  'name',
  'version',
  'architecture',
  'publisher',
  'installedOn',
  'installedBy',
  'sourceRpm',
  'sourceDeb',
];

function softwarePackagesFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly SoftwarePackage[] {
  return collectionResults
    .map((result) => (result.payload as ApiSoftwarePackages).packages)
    .flat()
    .filter((softwarePackage) => softwarePackage !== undefined)
    .map(translateSoftwarePackage);
}

/**
 * Component that displays `SoftwarePackages` flow results.
 */
@Component({
  selector: 'software-packagez',
  templateUrl: './software_packagez.ng.html',
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
export class SoftwarePackagez implements AfterViewInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<
    readonly SoftwarePackage[],
    readonly CollectionResult[]
  >({transform: softwarePackagesFromCollectionResults});

  protected readonly dataSource = new MatTableDataSource<SoftwarePackage>();
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
