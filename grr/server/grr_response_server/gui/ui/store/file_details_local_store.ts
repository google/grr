import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, Observable, of} from 'rxjs';
import {filter, map, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {ApiGetFileTextArgsEncoding} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {translateFile} from '../lib/api_translation/vfs';
import {File, FileIdentifier} from '../lib/models/vfs';
import {assertKeyNonNull, isNonNull} from '../lib/preconditions';

interface State {
  readonly mode?: ContentFetchMode;
  readonly file?: FileIdentifier;
  readonly fetchContentLength?: bigint;
  readonly textContent?: string;
  readonly blobContent?: ArrayBuffer;
  readonly totalLength?: bigint;
  readonly details?: File;
  readonly isRecollecting?: boolean;
}

/** Mode to define whether to load text or blob file contents. */
export enum ContentFetchMode {
  TEXT,
  BLOB,
}

interface FetchResult {
  readonly totalLength: bigint;
  readonly textContent?: string;
  readonly blobContent?: ArrayBuffer;
}

const ENCODING = ApiGetFileTextArgsEncoding.UTF_8;

/** Global store for showing scheduled flows. */
@Injectable()
export class FileDetailsLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new FileDetailsComponentStore(this.httpApiService);

  static readonly DEFAULT_PAGE_SIZE = BigInt(10000);

  selectFile(file: FileIdentifier|undefined) {
    this.store.selectFile(file);
  }

  fetchDetails() {
    this.store.fetchDetails();
  }

  setMode(mode: ContentFetchMode) {
    this.store.setMode(mode);
  }

  readonly file$ = this.store.file$;

  readonly mode$ = this.store.mode$;

  readonly details$ = this.store.details$;

  readonly textContent$ = this.store.textContent$;

  readonly blobContent$ = this.store.blobContent$;

  readonly totalLength$ = this.store.totalLength$;

  readonly hasMore$ = this.store.hasMore$;

  readonly isRecollecting$ = this.store.isRecollecting$;

  fetchMoreContent(length: bigint) {
    this.store.fetchMoreContent(length);
  }

  recollectFile() {
    this.store.recollectFile();
  }
}

class FileDetailsComponentStore extends ComponentStore<State> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});
  }

  // Clear whole state when selecting a new file.
  readonly selectFile =
      this.updater<FileIdentifier|undefined>((state, file) => ({file}));

  readonly setMode = this.updater<ContentFetchMode>((state, mode) => {
    if (state.mode === mode) {
      return state;
    } else {
      return {
        ...state,
        mode,
        totalLength: undefined,
        textContent: undefined,
        blobContent: undefined,
        fetchContentLength: undefined,
      };
    }
  });

  readonly file$ = this.select(state => state.file);

  readonly mode$ = this.select(state => state.mode)
                       .pipe(
                           map(mode => mode ?? ContentFetchMode.TEXT),
                       );

  readonly details$ = this.select(state => state.details);

  readonly textContent$ = this.select(state => state.textContent);

  readonly blobContent$ = this.select(state => state.blobContent);

  readonly totalLength$ = this.select(state => state.totalLength);

  private readonly fetchedLength$ = this.state$.pipe(
      map(({textContent, blobContent, mode}) => BigInt(
              (mode === ContentFetchMode.BLOB ? blobContent?.byteLength :
                                                textContent?.length) ??
              0)),
  );

  readonly hasMore$ =
      combineLatest(
          [this.select(state => state.totalLength), this.fetchedLength$])
          .pipe(map(
              ([totalLength, fetchedLength]) =>
                  BigInt(totalLength ?? 0) > fetchedLength,
              ));

  readonly fetchDetails = this.effect<void>(
      obs$ => obs$.pipe(
          withLatestFrom(this.state$),
          switchMap(([param, state]) => {
            assertKeyNonNull(state, 'file');
            return this.httpApiService.getFileDetails(
                state.file.clientId, state.file.pathType, state.file.path);
          }),
          map(translateFile),
          tap(file => {
            this.updateDetails(file as File);
          }),
          ));

  private fetch({file, mode, offset, length, totalLength}: {
    file: FileIdentifier,
    mode: ContentFetchMode,
    offset: bigint,
    length: bigint,
    totalLength?: bigint
  }): Observable<FetchResult|null> {
    if (mode === ContentFetchMode.BLOB) {
      const totalLength$ = totalLength !== undefined ?
          of(totalLength) :
          this.httpApiService.getFileBlobLength(
              file.clientId, file.pathType, file.path);

      const blobContent$ = this.httpApiService.getFileBlob(
          file.clientId, file.pathType, file.path, {
            offset: offset.toString(),
            length: length.toString(),
          });

      return combineLatest([totalLength$, blobContent$])
          .pipe(
              map(([totalLength, blobContent]) =>
                      (isNonNull(totalLength) && isNonNull(blobContent)) ?
                      {blobContent, totalLength} :
                      null),
          );

    } else {
      return this.httpApiService
          .getFileText(file.clientId, file.pathType, file.path, {
            encoding: ENCODING,
            offset: offset.toString(),
            length: length.toString(),
          })
          .pipe(
              map(response => response ? {
                totalLength: BigInt(response.totalSize ?? 0),
                textContent: response.content ?? '',
              } :
                                         null));
    }
  }

  readonly fetchMoreContent = this.effect<bigint>(
      obs$ => obs$.pipe(
          tap(fetchLength => {
            this.increaseFetchContentLength(fetchLength);
          }),
          withLatestFrom(this.state$),
          switchMap(([fetchLength, state]) => {
            assertKeyNonNull(state, 'file');

            const length = state.mode === ContentFetchMode.BLOB ?
                state.blobContent?.byteLength :
                state.textContent?.length;
            return this
                .fetch({
                  file: state.file,
                  mode: state.mode ?? ContentFetchMode.TEXT,
                  offset: BigInt(length ?? 0),
                  length: fetchLength,
                  totalLength: state.totalLength,
                })
                .pipe(
                    filter(isNonNull),
                    tap((result) => {
                      this.updateTotalLength(result.totalLength);
                      this.appendBlobContent(result.blobContent);
                      this.appendTextContent(result.textContent);
                    }),
                );
          }),
          ));

  readonly isRecollecting$ =
      this.select(state => state.isRecollecting)
          .pipe(
              map((isRecollecting) => isRecollecting ?? false),
          );

  readonly setIsRecollecting =
      this.updater<boolean>((state, isRecollecting) => ({
                              ...state,
                              isRecollecting,
                            }));

  readonly recollectFile = this.effect<void>(
      obs$ => obs$.pipe(
          tap(() => {
            this.setIsRecollecting(true);
          }),
          withLatestFrom(this.state$),
          switchMap(([param, state]) => {
            assertKeyNonNull(state, 'file');
            return this.httpApiService
                .updateVfsFileContent(
                    state.file.clientId, state.file.pathType, state.file.path)
                .pipe(
                    map(details => ({details, state})),
                );
          }),
          switchMap(({details, state}) => {
            if (!state.fetchContentLength) {
              return of({details, content: undefined});
            }

            return this
                .fetch({
                  file: state.file,
                  mode: state.mode ?? ContentFetchMode.TEXT,
                  offset: BigInt(0),
                  length: state.fetchContentLength,
                  totalLength: undefined,
                })
                .pipe(map(content => ({details, content})));
          }),
          tap(({details, content}) => {
            this.setIsRecollecting(false);
            this.updateDetails(translateFile(details) as File);
            this.updateTotalLength(content?.totalLength);
            this.setTextContent(content?.textContent);
            this.setBlobContent(content?.blobContent);
          }),
          ));

  private readonly updateTotalLength =
      this.updater<bigint|undefined>((state, totalLength) => ({
                                       ...state,
                                       totalLength,
                                     }));

  private readonly appendTextContent =
      this.updater<string|undefined>((state, textContent) => {
        if (textContent === undefined) {
          return state;
        }
        return {
          ...state,
          textContent: (state.textContent ?? '') + (textContent ?? ''),
        };
      });

  private readonly appendBlobContent =
      this.updater<ArrayBuffer|undefined>((state, appendBuffer) => {
        if (appendBuffer === undefined || state.blobContent === undefined) {
          return {
            ...state,
            blobContent: state.blobContent ?? appendBuffer,
          };
        }
        const oldLength = state.blobContent.byteLength;
        const blobContent = new Uint8Array(oldLength + appendBuffer.byteLength);
        blobContent.set(new Uint8Array(state.blobContent), 0);
        blobContent.set(new Uint8Array(appendBuffer), oldLength);

        return {
          ...state,
          blobContent: blobContent.buffer,
        };
      });

  private readonly setTextContent = this.updater<string|undefined>(
      (state, textContent) => ({...state, textContent}));

  private readonly setBlobContent = this.updater<ArrayBuffer|undefined>(
      (state, blobContent) => ({...state, blobContent}));

  private readonly increaseFetchContentLength = this.updater<bigint>(
      (state, length) => ({
        ...state,
        fetchContentLength: (state.fetchContentLength ?? BigInt(0)) + length,
      }));

  private readonly updateDetails =
      this.updater<File>((state, details) => ({...state, details}));
}
