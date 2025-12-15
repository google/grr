import {DestroyRef, inject} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {
  patchState,
  signalStore,
  withMethods,
  withProps,
  withState,
} from '@ngrx/signals';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  BrowseFilesystemEntry,
  BrowseFilesystemResult,
  Directory,
  PathSpecPathType,
} from '../lib/models/vfs';

const EMPTY_ROOT_DIRECTORY: Directory = {
  name: '',
  path: '/',
  pathtype: PathSpecPathType.OS,
  isDirectory: true,
};

interface FileExplorerStoreState {
  clientId: string | undefined;
  fileSystemTree: BrowseFilesystemEntry | undefined;

  // Paths that are currently being refreshed. This is used to prevent
  // refreshing the same path multiple times and indicate to the user that the
  // folder content is being refreshed. This only works as long as the File
  // Explorer page is open.
  currentlyRefreshingPaths: Set<string>;
}

function getInitialState(): FileExplorerStoreState {
  return {
    clientId: undefined,
    fileSystemTree: {
      file: EMPTY_ROOT_DIRECTORY,
      children: undefined,
    },

    currentlyRefreshingPaths: new Set(),
  };
}

/**
 * Store for the VFS of a client.
 * - The lifecycle of this store is tied to the VFS page.
 */
// tslint:disable-next-line:enforce-name-casing
export const FileExplorerStore = signalStore(
  withState<FileExplorerStoreState>(getInitialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    destroyRef: inject(DestroyRef),
  })),
  withMethods(({httpApiService, destroyRef, ...store}) => ({
    initialize(clientId: string, path: string): void {
      patchState(store, {clientId});
      httpApiService
        .browseFilesystem(clientId, path, {includeDirectoryTree: true})
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((result: BrowseFilesystemResult) => {
          if (result.rootEntry) {
            patchState(store, {fileSystemTree: result.rootEntry});
          }
        });
    },
    fetchChildren(parent: BrowseFilesystemEntry): void {
      const clientId = store.clientId();
      if (clientId === undefined || store.fileSystemTree() === undefined) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      httpApiService
        .browseFilesystem(clientId, parent.file!.path!, {
          includeDirectoryTree: false,
        })
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((result: BrowseFilesystemResult) => {
          // An empty list indicates that the children are loaded but empty.
          // `undefined` children indicates that the children are not loaded
          // yet.
          parent.children = result.rootEntry?.children ?? [];
          // Create a new object reference for fileSystemTree to trigger
          // reactivity.
          patchState(store, {fileSystemTree: {...store.fileSystemTree()!}});
        });
    },
    refreshVfsFolder(parent: BrowseFilesystemEntry, maxDepth?: number): void {
      const clientId = store.clientId();
      if (clientId === undefined) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      const file = parent.file;

      if (file === undefined) {
        throw new Error('Parent entry does not have a file.');
      }
      if (store.currentlyRefreshingPaths().has(file.path)) {
        return;
      }

      const currentlyRefreshingPaths = store.currentlyRefreshingPaths();
      currentlyRefreshingPaths.add(file.path);
      patchState(store, {currentlyRefreshingPaths});

      httpApiService
        .refreshVfsFolder(
          {
            clientId,
            pathType: file.pathtype,
            path: file.path,
          },
          maxDepth,
        )
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((result: BrowseFilesystemResult) => {
          const currentlyRefreshingPaths = store.currentlyRefreshingPaths();
          currentlyRefreshingPaths.delete(file.path);

          // An empty list indicates that the children are loaded but empty.
          // `undefined` children indicates that the children are not loaded
          // yet.
          parent.children = result.rootEntry?.children ?? [];
          patchState(store, {
            // Create a new object reference for fileSystemTree to trigger
            // reactivity.
            fileSystemTree: {...store.fileSystemTree()!},
            currentlyRefreshingPaths,
          });
        });
    },
  })),
);
