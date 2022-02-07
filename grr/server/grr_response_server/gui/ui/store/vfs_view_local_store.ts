import {HttpErrorResponse} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {forkJoin, Observable, of, throwError} from 'rxjs';
import {catchError, map, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {PathSpecPathType} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {translateFile} from '../lib/api_translation/vfs';
import {Directory, File, isSubDirectory, pathDepth, scanPath} from '../lib/models/vfs';
import {assertNonNull, isNonNull} from '../lib/preconditions';
import {addToMap, deepFreeze, mergeMaps, toMap} from '../lib/type_utils';

/**
 * A hierarchy of directories with children.
 */
export type Hierarchy = ReadonlyArray<DirectoryListing>;

interface State {
  readonly clientId: string|null;

  /** The user selected path, which can point to a Directory or File. */
  readonly path: string|null;

  /** All files and directories that have been loaded from the backend. */
  // When multiple Files exist for one path (e.g. one OS, one TSK), save the
  // latter one.
  readonly entries: ReadonlyMap<string, File|Directory>;

  // We do not embed `children` in entries in the internal State, because
  // directory data is queried concurrently. Embedding children requires the
  // parent directory to be present before children can be embedded. With
  // concurrent queries, the children data might arrive before the parent
  // directory.
  /** Map from parent path -> child paths. */
  readonly children: ReadonlyMap<string, ReadonlyArray<string>>;

  readonly isLoadingDirectory: ReadonlyMap<string, boolean>;

  readonly isListingCurrentDirectory: boolean;

  readonly expanded: ReadonlyMap<string, boolean>;
}

/** A Directory with children directories and files. */
export interface DirectoryListing extends Directory {
  // For simplicity, we embed children of the current working directory only,
  // e.g. this array contains Directory, not DirectoryListings. This avoids
  // reconstructing all directory tree branches, since the UI typically only
  // shows one path down the tree.
  readonly children: ReadonlyArray<Directory|File>;
}

/** A node in a tree containing directories and their subdirectories. */
export interface DirectoryNode extends Directory {
  readonly children?: ReadonlyArray<DirectoryNode>;
  readonly loading: boolean;
}

const ROOT = deepFreeze<Directory>({
  path: '/',
  name: '/',
  isDirectory: true,
  pathtype: PathSpecPathType.OS,
});

const toPathMap = (entries: ReadonlyArray<Directory|File>) =>
    toMap(entries, (entry) => entry.path);

const listDirectory =
    (path: string|null, state: State): File|DirectoryListing|null => {
      const dir = path ? state.entries.get(path) : null;
      if (!dir || !dir.isDirectory) {
        return dir ?? null;
      }
      const childPaths = state.children.get(dir.path) ?? [];
      const children =
          childPaths.map(path => state.entries.get(path)).filter(isNonNull);
      return {
        ...dir,
        children,
      };
    };

const toTree = (path: string|null, state: State): DirectoryNode|null => {
  const dir = path ? state.entries.get(path) : null;
  if (!path || !dir || !dir.isDirectory) {
    return null;
  }
  const childPaths = state.children.get(dir.path);
  const children = childPaths ?
      childPaths.map(path => toTree(path, state)).filter(isNonNull) :
      undefined;

  return {
    ...dir,
    children,
    loading: state.isLoadingDirectory.get(path) ?? false,
  };
};

class VfsViewComponentStore extends ComponentStore<State> {
  constructor(
      private readonly httpApiService: HttpApiService,
  ) {
    super({
      clientId: null,
      path: null,
      entries: new Map(),
      children: new Map(),
      isLoadingDirectory: new Map(),
      isListingCurrentDirectory: false,
      expanded: new Map(),
    });

    this.path$
        .pipe(
            withLatestFrom(this.clientId$),
            )
        .subscribe(([path, clientId]) => {
          if (path && clientId) {
            this.fetchPathHierarchy({clientId, path});
          }
        });
  }

  private readonly clientId$ = this.select(state => state.clientId);

  private readonly path$ = this.select(state => state.path);

  readonly directoryTree$ = this.select(state => toTree('/', state));

  readonly currentFile$ = this.select(state => {
    if (!state.path) {
      return null;
    }

    const entry = state.entries.get(state.path);

    if (!entry || entry.isDirectory) {
      return null;
    }

    return entry;
  });

  readonly currentDirectory$ = this.select(state => {
    if (!state.path) {
      return null;
    }

    // Iterate from deepest path to top-level path.
    for (const path of [...scanPath(state.path)].reverse()) {
      const entry = listDirectory(path, state);
      if (entry?.isDirectory) {
        return entry;
      }
    }

    return null;
  });

  readonly resetClientId = this.updater<string|null>((state, clientId) => {
    return {
      clientId,
      path: null,
      // Directories are added to entries when their parent directory is listed.
      // The root directory `/` is represented as `/fs/os` in the VFS, which
      // is an unintuitive implementation detail. Instead, we add the root
      // directory manually.
      entries: toPathMap([ROOT]),
      children: new Map(),
      isLoadingDirectory: new Map(),
      isListingCurrentDirectory: false,
      expanded: new Map(),
    };
  });

  private readonly markLoading = this.updater<{path: string, loading: boolean}>(
      (state, {path, loading}) => ({
        ...state,
        isLoadingDirectory: addToMap(state.isLoadingDirectory, path, loading),
      }));

  readonly navigateToPath = this.updater<string|null>(
      (state, path) => ({
        ...state,
        path,
      }),
  );

  readonly listCurrentDirectory = this.effect<{maxDepth?: number}|undefined>(
      obs$ => obs$.pipe(
          withLatestFrom(this.clientId$, this.path$),
          switchMap(([opts, clientId, path]) => {
            assertNonNull(clientId, 'clientId');
            assertNonNull(path, 'path');

            return of(null).pipe(
                tap(() => {
                  this.setListingCurrentDirectory(true);
                  this.markLoading({path, loading: true});
                }),
                switchMap(
                    () => this.httpApiService.refreshVfsFolder(
                        clientId, PathSpecPathType.OS, path, opts)),
                map(res => res.items?.map(translateFile) ?? []),
                tap(children => {
                  this.saveListingForPath({path, children});
                  this.setListingCurrentDirectory(false);
                }),
                withLatestFrom(this.state$),
                tap(([, state]) => {
                  // Re-load all child-paths of the refreshed directory that are
                  // visibily expandend in the UI.
                  const rootDepth = pathDepth(path);
                  const maxDepth = opts?.maxDepth ?? 1;
                  this.expandDirectories([...state.expanded.keys()].filter(
                      (subpath) => state.expanded.get(subpath) &&
                          isSubDirectory(subpath, path) &&
                          pathDepth(subpath) - rootDepth <= maxDepth));
                }),
            );
          }),
          ));

  readonly expandDirectories = this.effect<ReadonlyArray<string>>(
      obs$ => obs$.pipe(
          tap((paths) => {
            this.patchState(
                state => ({
                  expanded: mergeMaps(
                      state.expanded, toMap(paths, (path) => path, () => true)),
                }));
          }),
          withLatestFrom(this.state$),
          switchMap(([paths, state]) => {
            const clientId = state.clientId;
            assertNonNull(clientId, 'clientId');

            const pathListings$ =
                paths.filter(path => !state.isLoadingDirectory.get(path))
                    .map(path => this.fetchListingForPath(clientId, path));

            return forkJoin(pathListings$);
          }),
          ));

  readonly collapseDirectories = this.updater<ReadonlyArray<string>>(
      (state, paths) => ({
        ...state,
        expanded: mergeMaps(
            state.expanded, toMap(paths, (path) => path, () => false)),
      }),
  );

  readonly setListingCurrentDirectory = this.updater<boolean>(
      (state, isListingCurrentDirectory) =>
          ({...state, isListingCurrentDirectory}));

  readonly isListingCurrentDirectory$ =
      this.select(state => state.isListingCurrentDirectory);

  private readonly saveListingForPath =
      this.updater<{path: string, children: ReadonlyArray<File|Directory>}>(
          (state, {path, children}) => {
            const newState = {
              ...state,
              entries: mergeMaps(state.entries, toPathMap(children)),
              children:
                  addToMap(state.children, path, children.map(c => c.path)),
              isLoadingDirectory:
                  addToMap(state.isLoadingDirectory, path, false),
            };
            return newState;
          });

  private listFiles(
      clientId: string, pathType: PathSpecPathType, path: string) {
    return this.httpApiService.listFiles(clientId, pathType, path)
        .pipe(map(res => res.items?.map(translateFile) ?? []));
  }

  private listFilesAllPathTypes(clientId: string, path: string) {
    return forkJoin([
             this.listFiles(clientId, PathSpecPathType.OS, path),
             this.listFiles(clientId, PathSpecPathType.TSK, path),
             this.listFiles(clientId, PathSpecPathType.NTFS, path),
           ])
        .pipe(map(listings => {
          const allChildren = ([] as Array<File|Directory>).concat(...listings);
          const mergedChildren = new Map<string, File|Directory>();
          for (const entry of allChildren) {
            const existing = mergedChildren.get(entry.path);
            if (existing && !existing.isDirectory && !entry.isDirectory &&
                existing.lastMetadataCollected > entry.lastMetadataCollected) {
              continue;
            }
            mergedChildren.set(entry.path, entry);
          }
          return Array.from(mergedChildren.values());
        }));
  }

  private fetchListingForPath(clientId: string, path: string) {
    return of(null).pipe(
        tap(() => {
          this.markLoading({path, loading: true});
        }),
        switchMap(() => this.listFilesAllPathTypes(clientId, path)),
        tap({
          next: (children) => {
            this.saveListingForPath({path, children});
          },
          error: () => {
            this.markLoading(({path, loading: false}));
          },
        }),
        // The last path segment could be a File - `listFiles` will fail
        // for the file. Until we know more specific use cases and refine
        // the behavior for the VFS, ignore errors.
        catchError(
            (err: HttpErrorResponse) =>
                err.status === 500 ? of(null) : throwError(err)),
    );
  }

  // TODO: Handle the case where the selected path points to a
  // file.
  /** Concurrently lists all directories in the current hierarchy. */
  private readonly fetchPathHierarchy =
      this.effect<{clientId: string, path: string}>(
          obs$ => obs$.pipe(
              switchMap(
                  ({clientId, path}) => forkJoin(
                      scanPath(path).map(
                          segment =>
                              this.fetchListingForPath(clientId, segment)),
                      )),
              ));
}

/** Store for managing virtual filesystem state. */
@Injectable()
export class VfsViewLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new VfsViewComponentStore(this.httpApiService);

  /** The selected file, if the selected path points to a file. */
  readonly currentFile$: Observable<File|null> = this.store.currentFile$;

  /**
   * The selected directory. if the selected path points to a file, the file's
   * parent directory will be emitted.
   */
  readonly currentDirectory$: Observable<DirectoryListing|null> =
      this.store.currentDirectory$;

  readonly directoryTree$: Observable<DirectoryNode|null> =
      this.store.directoryTree$;

  readonly isListingCurrentDirectory$ = this.store.isListingCurrentDirectory$;

  listCurrentDirectory(opts?: {maxDepth: number}) {
    this.store.listCurrentDirectory(opts);
  }

  /** Navigates to the given path and lists all directories in the hierarchy. */
  navigateToPath(path: string|null|Observable<string|null>) {
    this.store.navigateToPath(path);
  }

  /** Resets the store and selects a new client id. */
  resetClientId(clientId: string|null) {
    this.store.resetClientId(clientId);
  }

  expandDirectories(paths: ReadonlyArray<string>) {
    this.store.expandDirectories(paths);
  }

  collapseDirectories(paths: ReadonlyArray<string>) {
    this.store.collapseDirectories(paths);
  }
}
