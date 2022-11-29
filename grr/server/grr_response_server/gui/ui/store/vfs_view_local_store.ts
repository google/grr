import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {forkJoin, NEVER, Observable, of} from 'rxjs';
import {map, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {PathSpecPathType} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {translateBrowseFilesytemResult} from '../lib/api_translation/vfs';
import {Directory, File, isSubDirectory, pathDepth, scanPath} from '../lib/models/vfs';
import {assertNonNull, isNonNull} from '../lib/preconditions';
import {addToMap, deepFreeze, mergeMaps, toMap, transformMapValues} from '../lib/type_utils';

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
            withLatestFrom(this.state$),
            switchMap(([path, state]) => {
              if (!path || !state.clientId) {
                return NEVER;
              }

              const segments = scanPath(path);
              const parent = segments[segments.length - 2];
              if (parent && state.children.has(parent)) {
                return this.fetchListingForPath(state.clientId, path);
              } else {
                return this.fetchDirectoryTreeForPath(state.clientId, path);
              }
            }),
            )
        .subscribe();
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
          withLatestFrom(this.clientId$, this.currentDirectory$),
          switchMap(([opts, clientId, directory]) => {
            assertNonNull(clientId, 'clientId');
            assertNonNull(directory, 'directory');
            const {pathtype, path} = directory;

            return of(null).pipe(
                tap(() => {
                  this.setListingCurrentDirectory(true);
                  this.markLoading({path, loading: true});
                }),
                switchMap(
                    () => this.httpApiService.refreshVfsFolder(
                        clientId, pathtype, path,
                        isNonNull(opts?.maxDepth) ?
                            {maxDepth: opts?.maxDepth.toString()} :
                            undefined)),
                map(translateBrowseFilesytemResult),
                tap(result => {
                  this.saveListingForPaths(result);
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

  private readonly saveListingForPaths =
      this.updater<Map<string, ReadonlyArray<File|Directory>>>(
          (state, entries) => {
            const allChildren = Array.from(entries.values()).flatMap(e => e);
            const newState = {
              ...state,
              entries: mergeMaps(state.entries, toPathMap(allChildren)),
              children: mergeMaps(
                  state.children,
                  transformMapValues(
                      entries, children => children.map(e => e.path))),
              isLoadingDirectory: mergeMaps(
                  state.isLoadingDirectory,
                  transformMapValues(entries, () => false))
            };
            return newState;
          });

  private listFilesAllPathTypes(
      clientId: string, path: string, includeDirectoryTree: boolean) {
    return this.httpApiService
        .browseFilesystem(clientId, path, {includeDirectoryTree})
        .pipe(
            map(translateBrowseFilesytemResult),
        );
  }

  private fetchListingForPath(clientId: string, path: string) {
    return of(null).pipe(
        tap(() => {
          this.markLoading({path, loading: true});
        }),
        switchMap(() => this.listFilesAllPathTypes(clientId, path, false)),
        tap({
          next: (results) => {
            this.saveListingForPaths(results);
          },
          error: () => {
            this.markLoading(({path, loading: false}));
          },
        }),
    );
  }

  private fetchDirectoryTreeForPath(clientId: string, path: string) {
    return of(null).pipe(
        tap(() => {
          this.patchState(state => ({
                            isLoadingDirectory: mergeMaps(
                                state.isLoadingDirectory,
                                toMap(scanPath(path), (p) => p, () => true))
                          }));
        }),
        switchMap(() => this.listFilesAllPathTypes(clientId, path, true)),
        tap({
          next: (results) => {
            this.saveListingForPaths(results);
          },
          error: () => {
            this.patchState(state => ({
                              isLoadingDirectory: mergeMaps(
                                  state.isLoadingDirectory,
                                  toMap(scanPath(path), (p) => p, () => false))
                            }));
          },
        }),
    );
  }
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
