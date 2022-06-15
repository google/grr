import {CollectionViewer, DataSource} from '@angular/cdk/collections';
import {NestedTreeControl, TreeControl} from '@angular/cdk/tree';
import {ChangeDetectionStrategy, Component, ViewChild} from '@angular/core';
import {MatTableDataSource} from '@angular/material/table';
import {ActivatedRoute} from '@angular/router';
import {SplitAreaDirective, SplitComponent} from 'angular-split';
import {Observable} from 'rxjs';
import {map, takeUntil, tap, withLatestFrom} from 'rxjs/operators';

import {Directory, File, scanPath} from '../../lib/models/vfs';
import {isNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {DirectoryNode, VfsViewLocalStore} from '../../store/vfs_view_local_store';

class DirectoryDataSource implements DataSource<DirectoryNode> {
  constructor(
      private readonly vfsViewLocalStore: VfsViewLocalStore,
      private readonly treeControl: TreeControl<DirectoryNode, string>,
  ) {
    this.treeControl.expansionModel.changed.subscribe(change => {
      this.vfsViewLocalStore.expandDirectories(change.added);
      this.vfsViewLocalStore.collapseDirectories(change.removed);
    });
  }

  connect(collectionViewer: CollectionViewer):
      Observable<readonly DirectoryNode[]> {
    return this.vfsViewLocalStore.directoryTree$.pipe(
        map(node => node ? [node] : []),
    );
  }

  disconnect(collectionViewer: CollectionViewer): void {}
}

declare interface DirectoryTableRow {
  readonly isDirectory: boolean;
  readonly path: string;
  readonly name: string;
  readonly size?: bigint;
  readonly atime?: Date;
  readonly mtime?: Date;
  readonly ctime?: Date;
  readonly btime?: Date;
}

const DIRECTORY_TABLE_COLUMNS: ReadonlyArray<keyof DirectoryTableRow> = [
  'isDirectory',
  'name',
  'size',
  'atime',
  'mtime',
  'ctime',
  'btime',
];

const toRow: (entry: File|Directory) => DirectoryTableRow = (entry) => {
  const statEntry = entry.isDirectory ? null : entry.stat;
  return {
    isDirectory: entry.isDirectory,
    path: entry.path,
    name: entry.name,
    size: statEntry?.stSize,
    atime: statEntry?.stAtime,
    mtime: statEntry?.stMtime,
    ctime: statEntry?.stCtime,
    btime: statEntry?.stBtime,
  };
};

/** Section in ClientPage that shows the virtual filesystem view. */
@Component({
  selector: 'app-vfs-section',
  templateUrl: './vfs_section.ng.html',
  styleUrls: ['./vfs_section.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    VfsViewLocalStore,
  ]
})
export class VfsSection {
  readonly ngOnDestroy = observeOnDestroy(this);

  readonly selectedFileId$ = this.vfsViewLocalStore.currentFile$.pipe(
      withLatestFrom(this.selectedClientGlobalStore.clientId$),
      map(([file, clientId]) => file && clientId ?
              {path: file.path, pathType: file.pathtype, clientId} :
              null));

  readonly selectedDirectory$ = this.vfsViewLocalStore.currentDirectory$;

  readonly isListingCurrentDirectory$ =
      this.vfsViewLocalStore.isListingCurrentDirectory$;

  readonly treeControl = new NestedTreeControl<DirectoryNode, string>(
      node => node.children as DirectoryNode[], {trackBy: node => node.path});

  readonly treeDataSource =
      new DirectoryDataSource(this.vfsViewLocalStore, this.treeControl);

  readonly tableDataSource = new MatTableDataSource<DirectoryTableRow>();

  readonly displayedTableColumns = DIRECTORY_TABLE_COLUMNS;

  @ViewChild('split') split!: SplitComponent;
  @ViewChild('area1') area1!: SplitAreaDirective;
  @ViewChild('area2') area2!: SplitAreaDirective;

  selectedTreePath: string|null = null;
  selectedTablePath: string|null = null;

  constructor(
      readonly route: ActivatedRoute,
      private readonly vfsViewLocalStore: VfsViewLocalStore,
      private readonly selectedClientGlobalStore: SelectedClientGlobalStore,
  ) {
    this.selectedClientGlobalStore.clientId$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe(clientId => {
          this.vfsViewLocalStore.resetClientId(clientId);
        });

    this.route.paramMap
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            map(params => params.get('path') ?? '/'),
            )
        .subscribe(path => {
          this.vfsViewLocalStore.navigateToPath(path);
          // Mark path segments that are specified in the URL always as expanded
          // tree nodes before they are actually loaded from the API by passing
          // their keys directly into the TreeControl's SelectionModel.
          this.treeControl.expansionModel.select(...scanPath(path));
        });

    this.vfsViewLocalStore.currentDirectory$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            tap(dir => {
              this.selectedTreePath = dir?.path ?? null;
            }),
            map(dir => (dir?.children ?? []).map(toRow)),
            )
        .subscribe(entries => {
          this.tableDataSource.data = entries;
        });

    this.vfsViewLocalStore.currentFile$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe(file => {
          this.selectedTablePath = file?.path ?? null;
        });
  }

  canExpand(index: number, node: DirectoryNode) {
    // Mark as expandable if we don't know whether the directory has children,
    // or we know it has more than 0 children. The only case where a folder is
    // not expendable if we know it has exactly 0 children.
    return isNull(node.children) || node.children.length > 0;
  }

  triggerListDirectory(event: MouseEvent) {
    event.preventDefault();
    this.vfsViewLocalStore.listCurrentDirectory({maxDepth: 1});
  }

  triggerDeepListDirectory(event: MouseEvent) {
    event.preventDefault();
    this.vfsViewLocalStore.listCurrentDirectory({maxDepth: 5});
  }

  trackByPath(index: number, item: DirectoryTableRow) {
    return item.path;
  }
}
