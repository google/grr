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

import {SoftwarePackages as ApiSoftwarePackages} from '../../../lib/api/api_interfaces';
import {translateSoftwarePackage} from '../../../lib/api/translation/flow';
import {SoftwarePackage} from '../../../lib/models/flow';
import {isHuntResult} from '../../../lib/models/hunt';
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

interface SoftwarePackageWithClientId extends SoftwarePackage {
  clientId: string;
}

function softwarePackagesWithClientIdFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly SoftwarePackageWithClientId[] {
  return collectionResults
    .map((result) => {
      const softwarePackages = (result.payload as ApiSoftwarePackages).packages;
      const softwarePackagesWithClientId: SoftwarePackageWithClientId[] = [];
      for (const softwarePackage of softwarePackages ?? []) {
        if (!softwarePackage) {
          continue;
        }
        softwarePackagesWithClientId.push({
          ...translateSoftwarePackage(softwarePackage),
          clientId: result.clientId,
        });
      }
      return softwarePackagesWithClientId;
    })
    .flat();
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
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  readonly softwarePackages = computed(() =>
    softwarePackagesWithClientIdFromCollectionResults(this.collectionResults()),
  );

  protected readonly dataSource = new MatTableDataSource<SoftwarePackage>();
  protected readonly displayedColumns = computed(() => {
    if (this.collectionResults().some(isHuntResult)) {
      return ['clientId', ...COLUMNS];
    }
    return COLUMNS;
  });

  constructor() {
    effect(() => {
      if (this.softwarePackages().length > 0) {
        this.dataSource.data = this.softwarePackages().slice();
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
