import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {Observable} from 'rxjs';
import {map, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {ApiGetFileTextArgsEncoding, ApiGetFileTextResult, PathSpecPathType} from '../lib/api/api_interfaces';
import {translateFile} from '../lib/api_translation/vfs';
import {File} from '../lib/models/vfs';
import {assertKeyNonNull} from '../lib/preconditions';

interface State {
  readonly file?: FileIdentifier;
  readonly textContent?: string;
  readonly totalSize?: bigint;
  readonly details?: File;
}

interface FileIdentifier {
  readonly clientId: string;
  readonly pathType: PathSpecPathType;
  readonly path: string;
}

const ENCODING = ApiGetFileTextArgsEncoding.UTF_8;

/** Global store for showing scheduled flows. */
@Injectable()
export class FileDetailsLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new FileDetailsComponentStore(this.httpApiService);

  selectFile(file: FileIdentifier|Observable<FileIdentifier>) {
    this.store.selectFile(file);
  }

  fetchDetails() {
    this.store.fetchDetails();
  }

  readonly details$ = this.store.details$;

  readonly textContent$ = this.store.textContent$;

  readonly totalTextLength$ = this.store.totalTextLength$;

  readonly hasMore$ = this.store.hasMore$;

  fetchMoreContent(length: bigint) {
    this.store.fetchMoreContent(length);
  }
}

class FileDetailsComponentStore extends ComponentStore<State> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});
  }

  // Clear whole state when selecting a new file.
  readonly selectFile = this.updater<FileIdentifier>((state, file) => ({file}));

  readonly details$ = this.select(state => state.details);

  readonly textContent$ = this.select(state => state.textContent);

  readonly totalTextLength$ = this.select(state => state.totalSize);

  readonly hasMore$ = this.state$.pipe(
      map(({totalSize, textContent}) =>
              BigInt(totalSize ?? 0) > BigInt(textContent?.length ?? 0)),
  );

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
            this.updateDetails(file);
          }),
          ));

  readonly fetchMoreContent = this.effect<bigint>(
      obs$ => obs$.pipe(
          withLatestFrom(this.state$),
          switchMap(([fetchLength, state]) => {
            assertKeyNonNull(state, 'file');
            return this.httpApiService.getFileText(
                state.file.clientId, state.file.pathType, state.file.path, {
                  encoding: ENCODING,
                  offset: state.textContent?.length ?? 0,
                  length: fetchLength,
                });
          }),
          tap(response => {
            this.appendTextContent(response);
          }),
          ));

  private readonly appendTextContent = this.updater<ApiGetFileTextResult>(
      (state, result) => ({
        ...state,
        textContent: (state.textContent ?? '') + (result.content ?? ''),
        totalSize: BigInt(result.totalSize ?? 0),
      }));

  private readonly updateDetails =
      this.updater<File>((state, details) => ({...state, details}));
}
