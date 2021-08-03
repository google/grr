import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {GetFileTextOptions, HttpApiService} from '@app/lib/api/http_api_service';
import {Observable} from 'rxjs';
import {filter, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {ApiGetFileTextResult, PathSpecPathType} from '../lib/api/api_interfaces';
import {isNonNull} from '../lib/preconditions';

interface State {
  readonly file?: FileIdentifier;
  readonly textContent?: string;
}

interface FileIdentifier {
  readonly clientId: string;
  readonly pathType: PathSpecPathType;
  readonly path: string;
}

/** Global store for showing scheduled flows. */
@Injectable()
export class FileDetailsLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new FileDetailsComponentStore(this.httpApiService);

  selectFile(file: FileIdentifier|Observable<FileIdentifier>) {
    this.store.selectFile(file);
  }

  readonly textContent$ = this.store.textContent$;

  fetchContent(opts: GetFileTextOptions|Observable<GetFileTextOptions>) {
    this.store.fetchContent(opts);
  }
}

class FileDetailsComponentStore extends ComponentStore<State> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});
  }

  readonly selectFile = this.updater<FileIdentifier>((state, file) => {
    return {file};
  });

  readonly textContent$ = this.select(state => state.textContent);

  private readonly file$ =
      this.select(state => state.file).pipe(filter(isNonNull));

  readonly fetchContent = this.effect<GetFileTextOptions>(
      obs$ => obs$.pipe(
          withLatestFrom(this.file$),
          switchMap(
              ([opts, {clientId, pathType, path}]) =>
                  this.httpApiService.getFileText(
                      clientId, pathType, path, opts)),
          tap(response => {
            this.updateTextContent(response);
          }),
          ));

  private readonly updateTextContent = this.updater<ApiGetFileTextResult>(
      (state, result) => ({
        ...state,
        textContent: result.content ?? '',
        totalSize: BigInt(result.totalSize ?? '0'),
      }));
}
