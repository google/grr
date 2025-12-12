import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  Input as RouterInput,
  signal,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatTreeModule} from '@angular/material/tree';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute, RouterModule} from '@angular/router';

import {getClientArchiveURL} from '../../../lib/api/http_api_service';
import {
  BrowseFilesystemEntry,
  isFile,
  isSymlink,
  StatEntry,
} from '../../../lib/models/vfs';
import {FileExplorerStore} from '../../../store/file_explorer_store';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleState,
  CollapsibleTitle,
} from '../../shared/collapsible_container';
import {FileContent} from '../../shared/collection_results/data_renderer/file_results_table/file_content';
import {
  FileResultsTable,
  FlowFileResult,
} from '../../shared/collection_results/data_renderer/file_results_table/file_results_table';
import {CopyButton} from '../../shared/copy_button';
import {SplitPanel} from '../../shared/split_panel/split_panel';

/**
 * Component displaying the file explorer for a client.
 */
@Component({
  selector: 'file-explorer',
  templateUrl: './file_explorer.ng.html',
  styleUrls: ['./file_explorer.scss'],
  imports: [
    CollapsibleContainer,
    CollapsibleContent,
    CollapsibleTitle,
    CommonModule,
    CopyButton,
    FileContent,
    FileResultsTable,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatTreeModule,
    ReactiveFormsModule,
    RouterModule,
    SplitPanel,
  ],
  providers: [FileExplorerStore],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileExplorer {
  protected readonly fileExplorerStore = inject(FileExplorerStore);

  protected readonly isSymlink = isSymlink;

  private readonly route = inject(ActivatedRoute);
  private readonly queryParams = toSignal(this.route.queryParams);
  protected readonly queryPath = computed(() => this.queryParams()?.['path']);

  protected readonly searchQuery = signal<string>('');
  protected readonly matchingPaths = signal<string[]>([]);
  protected readonly invalidSearchQuery = signal(false);

  protected readonly CollapsibleState = CollapsibleState;

  protected readonly currentSelectedFsEntry =
    signal<BrowseFilesystemEntry | null>(null);
  protected readonly currentSelectedFsContent = signal<FlowFileResult[]>([]);

  @RouterInput() clientId!: string;

  protected readonly rootArchiveUrl: string;

  constructor() {
    this.rootArchiveUrl = getClientArchiveURL(this.clientId);

    inject(Title).setTitle('GRR | Client > File Explorer');

    const init = effect(() => {
      const queryPath = this.queryPath();
      if (queryPath) {
        this.fileExplorerStore.initialize(this.clientId, this.queryPath());
      } else {
        this.fileExplorerStore.initialize(this.clientId, '/');
      }
      // We only initialize the store once with the query params. We update the
      // query params when a file or folder is selected, but this should not
      // trigger another initialization of the store.
      init.destroy();
    });

    // Update the current selected file system entry and content when the query
    // path changes or the file system tree changes.
    // The query path changes when the user selected a file or folder in the
    // file explorer.
    // The file system tree changes when new data is fetched from the server.
    effect(() => {
      const queryPath = this.queryPath();
      const pathComponents = queryPath?.split('/');
      if (!pathComponents) {
        return;
      }

      let currentFsTree = this.fileExplorerStore.fileSystemTree();
      if (currentFsTree === undefined) {
        return;
      }
      for (const pathComponent of pathComponents.slice(1)) {
        const nextFsTree: BrowseFilesystemEntry | undefined =
          currentFsTree.children?.find(
            (child) => child.file?.name === pathComponent,
          );
        if (!nextFsTree) {
          break;
        }
        currentFsTree = nextFsTree;
      }
      this.currentSelectedFsEntry.set(currentFsTree);
      if (currentFsTree.file?.isDirectory) {
        this.updateCurrentSelectedContent(currentFsTree.children ?? []);
      } else {
        this.updateCurrentSelectedContent([currentFsTree]);
      }
    });

    effect(() => {
      const searchRegex = this.searchRegex();
      if (!searchRegex) {
        // If the search query is empty or invalid, we show all files.
        this.matchingPaths.set(['/']);
        return;
      }

      const matches: string[] = [];
      function searchFsEntry(fsEntry: BrowseFilesystemEntry): void {
        if (fsEntry.file?.path && searchRegex!.test(fsEntry.file?.path)) {
          if (fsEntry.file?.isDirectory) {
            matches.push(fsEntry.file?.path + '/');
          } else {
            matches.push(fsEntry.file?.path);
          }
          return;
        }
        for (const child of fsEntry.children ?? []) {
          searchFsEntry(child);
        }
      }
      searchFsEntry(this.fileExplorerStore.fileSystemTree()!);

      this.matchingPaths.set(matches);
    });
  }

  searchRegex(): RegExp | undefined {
    const searchQuery = this.searchQuery();
    if (!searchQuery) {
      return undefined;
    }
    try {
      const searchRegex = new RegExp(searchQuery, 'i');
      this.invalidSearchQuery.set(false);
      return searchRegex;
    } catch (err) {
      this.invalidSearchQuery.set(true);
      return undefined;
    }
  }

  private updateCurrentSelectedContent(
    fsEntries: BrowseFilesystemEntry[],
  ): void {
    const result: FlowFileResult[] = [];
    for (const fsEntry of fsEntries) {
      if (fsEntry.file === undefined) {
        continue;
      }
      const statEntry: StatEntry = {
        ...fsEntry.file.stat,
        pathspec: {
          path: fsEntry.file.stat?.pathspec?.path ?? fsEntry.file.path,
          pathtype:
            fsEntry.file.stat?.pathspec?.pathtype ?? fsEntry.file.pathtype,
          segments: fsEntry.file.stat?.pathspec?.segments ?? [],
        },
      };

      result.push({
        clientId: this.clientId,
        statEntry,
        hashes: isFile(fsEntry.file) ? fsEntry.file?.hash : {},
        isDirectory: fsEntry.file?.isDirectory,
        isFile: !fsEntry.file.isDirectory,
      });
    }
    this.currentSelectedFsContent.set(result);
  }

  protected hasOverlapWithSearchQuery(
    path: string,
    isDirectory: boolean,
  ): boolean {
    if (isDirectory && !path.endsWith('/')) {
      path += '/';
    }
    for (const matchingPath of this.matchingPaths()) {
      if (matchingPath.startsWith(path)) {
        return true;
      }
      if (path.startsWith(matchingPath)) {
        return true;
      }
    }
    return false;
  }
}
