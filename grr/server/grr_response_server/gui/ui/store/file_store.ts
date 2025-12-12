import {HttpErrorResponse} from '@angular/common/http';
import {DestroyRef, inject} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {tapResponse} from '@ngrx/operators';
import {
  patchState,
  signalStore,
  withMethods,
  withProps,
  withState,
} from '@ngrx/signals';
import {rxMethod} from '@ngrx/signals/rxjs-interop';
import {combineLatest, of, pipe} from 'rxjs';
import {map, switchMap} from 'rxjs/operators';

import {
  ApiGetFileTextArgsEncoding,
  PathSpecPathType,
} from '../lib/api/api_interfaces';
import {FileSpec} from '../lib/api/http_api_service';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {Directory, File, FileContent} from '../lib/models/vfs';

const DEFAULT_CONTENT_LENGTH = 1024;
const DEFAULT_CONTENT_OFFSET = 0;

/** Query for fetching a file. */
export interface FileQuery {
  readonly clientId: string;
  readonly pathType: PathSpecPathType;
  readonly path: string;
  readonly offset?: number;
  readonly length?: number;
  readonly hasFileContentAccess?: boolean;
}

interface FileStoreState {
  // Maps client id to path type to path to user access to the file.
  fileContentAccessMap: Map<
    string,
    Map<PathSpecPathType, Map<string, boolean>>
  >;
  // Maps client id to path type to path to file or directory.
  fileDetailsMap: Map<
    string,
    Map<PathSpecPathType, Map<string, File | Directory>>
  >;
  // Maps client id to path type to path to file content.
  fileTextMap: Map<
    string,
    Map<PathSpecPathType, Map<string, FileContent | undefined>>
  >;
  // Maps client id to path type to path to file blob.
  fileBlobMap: Map<
    string,
    Map<PathSpecPathType, Map<string, FileContent | undefined>>
  >;
  // Set of files that are currently being recollected. This is used to disable
  // the recollect button while the file is being recollected.
  recollectingFiles: Set<FileQuery>;
}

function getInitialState(): FileStoreState {
  return {
    fileContentAccessMap: new Map<
      string,
      Map<PathSpecPathType, Map<string, boolean>>
    >(),
    fileDetailsMap: new Map<
      string,
      Map<PathSpecPathType, Map<string, File | Directory>>
    >(),
    fileTextMap: new Map<
      string,
      Map<PathSpecPathType, Map<string, FileContent | undefined>>
    >(),
    fileBlobMap: new Map<
      string,
      Map<PathSpecPathType, Map<string, FileContent | undefined>>
    >(),
    recollectingFiles: new Set<FileQuery>(),
  };
}

/**
 * Store for file data displayed in the FileResultsTable.
 * The lifecycle of this store is tied to the FileResultsTable as it is not
 * expected that we access the data in different components.
 * When accessing a different client/flow the data needs to be reloaded.
 *
 */
// tslint:disable-next-line:enforce-name-casing
export const FileStore = signalStore(
  withState<FileStoreState>(getInitialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    destroyRef: inject(DestroyRef),
  })),
  withMethods(({httpApiService, destroyRef, ...store}) => ({
    fetchFileContentAccess: rxMethod<FileQuery | undefined>(
      pipe(
        switchMap((fileQuery: FileQuery | undefined) => {
          if (!fileQuery) return of(undefined);

          const fileSpec = {
            clientId: fileQuery.clientId,
            pathType: fileQuery.pathType,
            path: fileQuery.path,
          };
          return httpApiService.getFileAccess(fileSpec).pipe(
            tapResponse({
              next: (fileAccess: boolean) => {
                patchState(store, {
                  fileContentAccessMap: new Map(
                    updateFileContentAccessMap(
                      store.fileContentAccessMap(),
                      fileSpec,
                      fileAccess,
                    ),
                  ),
                });
              },
              error: (err: HttpErrorResponse) => {
                throw new Error(err.message);
              },
            }),
          );
        }),
      ),
    ),
    fetchFileDetails: rxMethod<FileQuery | undefined>(
      pipe(
        switchMap((fileQuery: FileQuery | undefined) => {
          if (!fileQuery) return of(undefined);
          if (fileQuery.hasFileContentAccess === false) return of(undefined);

          const fileSpec = {
            clientId: fileQuery.clientId,
            pathType: fileQuery.pathType,
            path: fileQuery.path,
          };
          return httpApiService.getFileDetails(fileSpec).pipe(
            tapResponse({
              next: (file: File | Directory) => {
                patchState(store, {
                  fileDetailsMap: new Map(
                    updateFileDetailsMap(
                      store.fileDetailsMap(),
                      fileSpec,
                      file,
                    ),
                  ),
                });
              },
              error: (err: HttpErrorResponse) => {
                // TODO: Revisit this once errors are handled.
                throw err;
              },
            }),
          );
        }),
      ),
    ),
    fetchTextFile: rxMethod<FileQuery | undefined>(
      pipe(
        switchMap((fileQuery: FileQuery | undefined) => {
          if (!fileQuery) return of(undefined);
          if (fileQuery.hasFileContentAccess === false) return of(undefined);

          const fileSpec = {
            clientId: fileQuery.clientId,
            pathType: fileQuery.pathType,
            path: fileQuery.path,
          };
          return httpApiService
            .getFileText(fileSpec, {
              offset: String(fileQuery.offset ?? DEFAULT_CONTENT_OFFSET),
              length: String(fileQuery.length ?? DEFAULT_CONTENT_LENGTH),
              encoding: ApiGetFileTextArgsEncoding.UTF_8,
            })
            .pipe(
              tapResponse({
                next: (fileContent: FileContent | null) => {
                  patchState(store, {
                    fileTextMap: new Map(
                      updateFileTextMap(
                        store.fileTextMap(),
                        fileSpec,
                        fileContent,
                      ),
                    ),
                  });
                },
                error: (err: HttpErrorResponse) => {
                  // TODO: Revisit this once errors are handled.
                  throw err;
                },
              }),
            );
        }),
      ),
    ),
    fetchBinaryFile: rxMethod<FileQuery | undefined>(
      pipe(
        switchMap((fileQuery: FileQuery | undefined) => {
          if (!fileQuery) return of(undefined);
          if (fileQuery.hasFileContentAccess === false) return of(undefined);

          const fileSpec = {
            clientId: fileQuery.clientId,
            pathType: fileQuery.pathType,
            path: fileQuery.path,
          };
          const length = httpApiService.getFileBlobLength(fileSpec);

          const fileBlob = httpApiService.getFileBlob(fileSpec, {
            offset: String(fileQuery.offset ?? DEFAULT_CONTENT_OFFSET),
            length: String(fileQuery.length ?? DEFAULT_CONTENT_LENGTH),
          });

          return combineLatest([length, fileBlob]).pipe(
            map(([length, fileBlob]) => {
              patchState(store, {
                fileBlobMap: new Map(
                  updateFileBlobMap(
                    store.fileBlobMap(),
                    fileSpec,
                    fileBlob,
                    length,
                  ),
                ),
              });
            }),
          );
        }),
      ),
    ),
    isRecollecting(fileQuery: FileQuery) {
      for (const recollectingFile of store.recollectingFiles()) {
        if (
          recollectingFile.clientId === fileQuery.clientId &&
          recollectingFile.pathType === fileQuery.pathType &&
          recollectingFile.path === fileQuery.path
        ) {
          return true;
        }
      }
      return false;
    },
    recollectFile(fileQuery: FileQuery) {
      const fileSpec = {
        clientId: fileQuery.clientId,
        pathType: fileQuery.pathType,
        path: fileQuery.path,
      };
      const recollectingFiles = store.recollectingFiles();
      recollectingFiles.add(fileQuery);
      patchState(store, {recollectingFiles});
      httpApiService
        .updateVfsFileContent(fileSpec)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((file: File | Directory) => {
          const recollectingFiles = store.recollectingFiles();
          recollectingFiles.delete(fileQuery);
          // The `updateVfsFileContent` httpApiService polls the VFS file until
          // it was re-collected and returns the updated file. We will still
          // need to fetch the text and blob content of the file.
          patchState(store, {
            fileDetailsMap: new Map(
              updateFileDetailsMap(store.fileDetailsMap(), fileSpec, file),
            ),
            recollectingFiles,
          });

          httpApiService
            .getFileText(fileSpec, {
              offset: String(fileQuery.offset ?? DEFAULT_CONTENT_OFFSET),
              length: String(fileQuery.length ?? DEFAULT_CONTENT_LENGTH),
              encoding: ApiGetFileTextArgsEncoding.UTF_8,
            })
            .pipe(takeUntilDestroyed(destroyRef))
            .subscribe((fileContent: FileContent | null) => {
              patchState(store, {
                fileTextMap: new Map(
                  updateFileTextMap(store.fileTextMap(), fileSpec, fileContent),
                ),
              });
            });

          const length = httpApiService.getFileBlobLength(fileSpec);
          const fileBlob = httpApiService.getFileBlob(fileSpec, {
            offset: String(fileQuery.offset ?? DEFAULT_CONTENT_OFFSET),
            length: String(fileQuery.length ?? DEFAULT_CONTENT_LENGTH),
          });
          return combineLatest([length, fileBlob])
            .pipe(takeUntilDestroyed(destroyRef))
            .subscribe(([length, fileBlob]) => {
              patchState(store, {
                fileBlobMap: new Map(
                  updateFileBlobMap(
                    store.fileBlobMap(),
                    fileSpec,
                    fileBlob,
                    length,
                  ),
                ),
              });
            });
        });
    },
  })),
);

function updateFileContentAccessMap(
  fileContentAccessMap: Map<
    string,
    Map<PathSpecPathType, Map<string, boolean>>
  >,
  fileSpec: FileSpec,
  access: boolean,
): Map<string, Map<PathSpecPathType, Map<string, boolean>>> {
  if (!fileContentAccessMap.has(fileSpec.clientId!)) {
    fileContentAccessMap.set(
      fileSpec.clientId!,
      new Map<PathSpecPathType, Map<string, boolean>>(),
    );
  }
  const clientMap = fileContentAccessMap.get(fileSpec.clientId!)!;
  if (!clientMap.has(fileSpec.pathType!)) {
    clientMap.set(fileSpec.pathType!, new Map<string, boolean>());
  }
  const fileTypemap = clientMap.get(fileSpec.pathType!)!;
  fileTypemap.set(fileSpec.path!, access);

  return fileContentAccessMap;
}

function updateFileDetailsMap(
  fileDetailsMap: Map<
    string,
    Map<PathSpecPathType, Map<string, File | Directory>>
  >,
  fileSpec: FileSpec,
  file: File | Directory,
): Map<string, Map<PathSpecPathType, Map<string, File | Directory>>> {
  if (!fileDetailsMap.has(fileSpec.clientId!)) {
    fileDetailsMap.set(
      fileSpec.clientId!,
      new Map<PathSpecPathType, Map<string, File | Directory>>(),
    );
  }
  const clientMap = fileDetailsMap.get(fileSpec.clientId!)!;
  if (!clientMap.has(fileSpec.pathType!)) {
    clientMap.set(fileSpec.pathType!, new Map<string, File | Directory>());
  }
  const fileTypemap = clientMap.get(fileSpec.pathType!)!;
  fileTypemap.set(fileSpec.path!, file);

  return fileDetailsMap;
}

function updateFileTextMap(
  fileTextMap: Map<
    string,
    Map<PathSpecPathType, Map<string, FileContent | undefined>>
  >,
  fileSpec: FileSpec,
  fileContent: FileContent | null,
): Map<string, Map<PathSpecPathType, Map<string, FileContent | undefined>>> {
  if (!fileTextMap.has(fileSpec.clientId!)) {
    fileTextMap.set(
      fileSpec.clientId!,
      new Map<PathSpecPathType, Map<string, FileContent | undefined>>(),
    );
  }
  const clientMap = fileTextMap.get(fileSpec.clientId!)!;
  if (!clientMap.has(fileSpec.pathType!)) {
    clientMap.set(
      fileSpec.pathType!,
      new Map<string, FileContent | undefined>(),
    );
  }
  const fileTypemap = clientMap.get(fileSpec.pathType!)!;
  fileTypemap.set(fileSpec.path!, fileContent ?? undefined);

  return fileTextMap;
}

function updateFileBlobMap(
  fileBlobMap: Map<
    string,
    Map<PathSpecPathType, Map<string, FileContent | undefined>>
  >,
  fileSpec: FileSpec,
  fileBlob: ArrayBuffer | null,
  length: bigint | null,
): Map<string, Map<PathSpecPathType, Map<string, FileContent | undefined>>> {
  if (!fileBlobMap.has(fileSpec.clientId!)) {
    fileBlobMap.set(
      fileSpec.clientId!,
      new Map<PathSpecPathType, Map<string, FileContent | undefined>>(),
    );
  }
  const clientMap = fileBlobMap.get(fileSpec.clientId!)!;
  if (!clientMap.has(fileSpec.pathType!)) {
    clientMap.set(
      fileSpec.pathType!,
      new Map<string, FileContent | undefined>(),
    );
  }
  const fileTypemap = clientMap.get(fileSpec.pathType!)!;
  if (fileBlob && length) {
    fileTypemap.set(fileSpec.path!, {
      blobContent: fileBlob,
      totalLength: length,
    });
  } else {
    fileTypemap.set(fileSpec.path!, undefined);
  }

  return fileBlobMap;
}
