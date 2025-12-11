import {HttpErrorResponse} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {Observable, of, throwError, timer} from 'rxjs';
import {
  catchError,
  exhaustMap,
  map,
  mapTo,
  shareReplay,
  takeWhile,
} from 'rxjs/operators';

import {
  ApprovalConfig,
  Client,
  ClientApproval,
  ClientApprovalRequest,
  ClientSnapshot,
  StartupInfo,
} from '../models/client';
import {UiConfig} from '../models/configuration';
import {
  ArtifactDescriptorMap,
  Binary,
  Flow,
  FlowDescriptor,
  FlowLogs,
  FlowState,
  ListAllOutputPluginLogsResult,
  ListFlowResultsResult,
  ScheduledFlow,
} from '../models/flow';
import {GlobComponentExplanation} from '../models/glob_expression';
import {
  Hunt,
  HuntApproval,
  HuntApprovalKey,
  HuntApprovalRequest,
  HuntState,
  ListHuntErrorsArgs,
  ListHuntErrorsResult,
  ListHuntLogsResult,
  ListHuntResultsArgs,
  ListHuntResultsResult,
  ListHuntsArgs,
  ListHuntsResult,
  SafetyLimits,
} from '../models/hunt';
import {OutputPlugin, OutputPluginDescriptor} from '../models/output_plugin';
import {GrrUser} from '../models/user';
import {
  BrowseFilesystemResult,
  Directory,
  File,
  FileContent,
} from '../models/vfs';
import {
  ClientApprovalKey,
  FileSpec,
  FlowResultsParams,
  GetFileBlobOptions,
  GetFileTextOptions,
  HttpApiService,
} from './http_api_service';
import {translateArtifactDescriptors} from './translation/artifact';
import {
  translateClient,
  translateClientApproval,
  translateClientLabel,
  translateClientSnapshot,
  translateClientStartupInfo,
} from './translation/client';
import {translateUiConfig} from './translation/configuration';
import {
  safeTranslateBinary,
  translateFlow,
  translateFlowDescriptor,
  translateFlowLogs,
  translateListAllOutputPluginLogsResult,
  translateListFlowResultsResult,
  translateScheduledFlow,
} from './translation/flow';
import {translateGlobComponentExplanation} from './translation/glob_expression';
import {
  toApiHuntState,
  toApiListHuntErrorsArgs,
  toApiListHuntResultsArgs,
  toApiListHuntsArgs,
  translateHunt,
  translateHuntApproval,
  translateListHuntErrorsResult,
  translateListHuntLogsResult,
  translateListHuntResultsResult,
  translateListHuntsResult,
} from './translation/hunt';
import {translateOutputPluginDescriptor} from './translation/output_plugin';
import {
  translateApproverSuggestions,
  translateGrrUser,
} from './translation/user';
import {
  translateApiGetFileTextResult,
  translateBrowseFilesystemResult,
  translateFile,
} from './translation/vfs';

import * as apiInterfaces from './api_interfaces';

/**
 * Wrapper around HttpClientService that translates the api response to the internal model types.
 */
@Injectable()
export class HttpApiWithTranslationService {
  constructor(private readonly httpApiService: HttpApiService) {}

  searchClients(
    args: apiInterfaces.ApiSearchClientsArgs,
  ): Observable<Client[]> {
    return this.httpApiService
      .searchClients(args)
      .pipe(map((results) => results.items?.map(translateClient) ?? []));
  }

  fetchClient(id: string, pollingInterval = 0): Observable<Client> {
    return this.httpApiService
      .fetchClient(id, pollingInterval)
      .pipe(map((apiClient) => translateClient(apiClient)));
  }

  requestClientApproval(
    args: ClientApprovalRequest,
  ): Observable<ClientApproval> {
    return this.httpApiService
      .requestClientApproval(args)
      .pipe(map((apiApproval) => translateClientApproval(apiApproval)));
  }

  fetchApprovalConfig(): Observable<ApprovalConfig> {
    return this.httpApiService.fetchApprovalConfig().pipe(
      // Replace empty string (protobuf default) with undefined.
      map((res) => (res.value?.['value'] as string) ?? undefined),
      map((optionalCcEmail) => ({optionalCcEmail})),
    );
  }

  fetchWebAuthType(): Observable<string> {
    return this.httpApiService.fetchWebAuthType().pipe(
      // Replace empty string (protobuf default) with undefined.
      map((res) => (res.value?.['value'] as string) ?? undefined),
    );
  }

  fetchExportCommandPrefix(): Observable<string> {
    return this.httpApiService.fetchExportCommandPrefix().pipe(
      // Replace empty string (protobuf default) with undefined.
      map((res) => (res.value?.['value'] as string) ?? undefined),
    );
  }

  listClientApprovals(
    clientId: string,
    pollingInterval = 0,
  ): Observable<ClientApproval[]> {
    return this.httpApiService
      .listClientApprovals(clientId, pollingInterval)
      .pipe(map((res) => res.items?.map(translateClientApproval) ?? []));
  }

  verifyClientAccess(clientId: string, poll = 0): Observable<boolean> {
    return timer(0, poll)
      .pipe(
        exhaustMap(() =>
          this.httpApiService.verifyClientAccess(clientId).pipe(
            map(() => true),
            catchError((err: HttpErrorResponse) => {
              if (err.status === 403) {
                return of(false);
              } else {
                return throwError(() => new Error(err.message));
              }
            }),
          ),
        ),
      )
      .pipe(
        takeWhile((hasAccess) => !hasAccess, true),
        shareReplay({bufferSize: 1, refCount: true}),
      );
  }

  fetchClientApproval(
    {clientId, requestor, approvalId}: ClientApprovalKey,
    pollingInterval = 0,
  ): Observable<ClientApproval> {
    return this.httpApiService
      .fetchClientApproval(
        {
          clientId,
          requestor,
          approvalId,
        },
        pollingInterval,
      )
      .pipe(map((apiApproval) => translateClientApproval(apiApproval)));
  }

  fetchFlow(clientId: string, flowId: string): Observable<Flow> {
    return this.httpApiService
      .fetchFlow(clientId, flowId)
      .pipe(map((apiFlow) => translateFlow(apiFlow)));
  }

  pollFlow(
    clientId: string,
    flowId: string,
    pollingInterval = 0,
  ): Observable<Flow> {
    return this.httpApiService
      .fetchFlow(clientId, flowId, pollingInterval)
      .pipe(
        map((apiFlow) => translateFlow(apiFlow)),
        takeWhile(
          (flow) =>
            flow.state !== FlowState.FINISHED && flow.state !== FlowState.ERROR,
          true,
        ),
        shareReplay({bufferSize: 1, refCount: true}),
      );
  }

  fetchFlowLogs(clientId: string, flowId: string): Observable<FlowLogs> {
    return this.httpApiService
      .fetchFlowLogs(clientId, flowId)
      .pipe(map((apiFlowLogs) => translateFlowLogs(apiFlowLogs)));
  }

  listAllFlowOutputPluginLogs(
    clientId: string,
    flowId: string,
  ): Observable<ListAllOutputPluginLogsResult> {
    return this.httpApiService
      .listAllFlowOutputPluginLogs(clientId, flowId)
      .pipe(map(translateListAllOutputPluginLogsResult));
  }

  createHunt(
    description: string,
    flowName: string,
    flowArgs: unknown,
    originalFlowRef: apiInterfaces.ApiFlowReference | undefined,
    originalHuntRef: apiInterfaces.ApiHuntReference | undefined,
    safetyLimits: SafetyLimits,
    rules: apiInterfaces.ForemanClientRuleSet,
    outputPlugins: readonly OutputPlugin[],
  ): Observable<Hunt> {
    return this.httpApiService
      .createHunt(
        description,
        flowName,
        flowArgs as apiInterfaces.Any,
        originalFlowRef,
        originalHuntRef,
        safetyLimits,
        rules,
        outputPlugins,
      )
      .pipe(map((hunt) => translateHunt(hunt)));
  }

  requestHuntApproval(args: HuntApprovalRequest): Observable<HuntApproval> {
    return this.httpApiService
      .requestHuntApproval(args)
      .pipe(map((huntApproval) => translateHuntApproval(huntApproval)));
  }

  listHuntApprovals(
    huntId: string,
    pollingInterval = 0,
  ): Observable<HuntApproval[]> {
    return this.httpApiService
      .listHuntApprovals(huntId, pollingInterval)
      .pipe(map((res) => res.items?.map(translateHuntApproval) ?? []));
  }

  fetchHunt(id: string, pollingInterval = 0): Observable<Hunt> {
    return this.httpApiService
      .fetchHunt(id, pollingInterval)
      .pipe(map((hunt) => translateHunt(hunt)));
  }

  verifyHuntAccess(huntId: string, poll = 0): Observable<boolean> {
    return timer(0, poll)
      .pipe(
        exhaustMap(() =>
          this.httpApiService.verifyHuntAccess(huntId).pipe(
            map(() => true),
            catchError((err: HttpErrorResponse) => {
              if (err.status === 403) {
                return of(false);
              } else {
                return throwError(() => new Error(err.message));
              }
            }),
          ),
        ),
      )
      .pipe(
        takeWhile((hasAccess) => !hasAccess, true),
        shareReplay({bufferSize: 1, refCount: true}),
      );
  }

  fetchHuntApproval(
    {huntId, approvalId, requestor}: HuntApprovalKey,
    pollingInterval = 0,
  ): Observable<HuntApproval> {
    return this.httpApiService
      .fetchHuntApproval({huntId, approvalId, requestor}, pollingInterval)
      .pipe(map((huntApproval) => translateHuntApproval(huntApproval)));
  }

  grantHuntApproval({
    huntId,
    approvalId,
    requestor,
  }: HuntApprovalKey): Observable<HuntApproval> {
    return this.httpApiService
      .grantHuntApproval({
        huntId,
        approvalId,
        requestor,
      })
      .pipe(map((huntApproval) => translateHuntApproval(huntApproval)));
  }

  patchHunt(
    huntId: string,
    patch: {
      state?: HuntState;
      clientLimit?: bigint;
      clientRate?: number;
    },
  ): Observable<Hunt> {
    return this.httpApiService
      .patchHunt(huntId, {
        state: patch.state ? toApiHuntState(patch.state) : undefined,
        clientLimit: patch.clientLimit,
        clientRate: patch.clientRate,
      })
      .pipe(map((hunt) => translateHunt(hunt)));
  }

  getHuntResultsByType(
    huntId: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiCountHuntResultsByTypeResult> {
    return this.httpApiService.getHuntResultsByType(huntId, pollingInterval);
  }

  listResultsForHunt(
    params: ListHuntResultsArgs,
    pollingInterval = 0,
  ): Observable<ListHuntResultsResult> {
    return this.httpApiService
      .listResultsForHunt(toApiListHuntResultsArgs(params), pollingInterval)
      .pipe(map((res) => translateListHuntResultsResult(res)));
  }

  listErrorsForHunt(
    params: ListHuntErrorsArgs,
    pollingInterval = 0,
  ): Observable<ListHuntErrorsResult> {
    return this.httpApiService
      .listErrorsForHunt(toApiListHuntErrorsArgs(params))
      .pipe(map((res) => translateListHuntErrorsResult(res)));
  }

  getHuntClientCompletionStats(
    args: apiInterfaces.ApiGetHuntClientCompletionStatsArgs,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiGetHuntClientCompletionStatsResult> {
    return this.httpApiService.getHuntClientCompletionStats(
      args,
      pollingInterval,
    );
  }

  listHunts(
    args: ListHuntsArgs,
    pollingInterval = 0,
  ): Observable<ListHuntsResult> {
    return this.httpApiService
      .listHunts(toApiListHuntsArgs(args), pollingInterval)
      .pipe(map((res) => translateListHuntsResult(res)));
  }

  fetchHuntLogs(huntId: string): Observable<ListHuntLogsResult> {
    return this.httpApiService
      .fetchHuntLogs(huntId)
      .pipe(map((res) => translateListHuntLogsResult(res)));
  }

  grantClientApproval({
    clientId,
    requestor,
    approvalId,
  }: ClientApprovalKey): Observable<ClientApproval> {
    return this.httpApiService
      .grantClientApproval({
        clientId,
        requestor,
        approvalId,
      })
      .pipe(map((apiApproval) => translateClientApproval(apiApproval)));
  }

  listFlowDescriptors(): Observable<FlowDescriptor[]> {
    return this.httpApiService
      .listFlowDescriptors()
      .pipe(
        map((apiDescriptors) => apiDescriptors.map(translateFlowDescriptor)),
      );
  }

  getArtifactDescriptorMap(): Observable<ArtifactDescriptorMap> {
    return this.httpApiService
      .listArtifactDescriptors()
      .pipe(map((res) => translateArtifactDescriptors(res.items ?? [])));
  }

  listOutputPluginDescriptors(): Observable<OutputPluginDescriptor[]> {
    return this.httpApiService
      .listOutputPluginDescriptors()
      .pipe(map((res) => res.map(translateOutputPluginDescriptor) ?? []));
  }

  listFlowsForClient(
    args: apiInterfaces.ApiListFlowsArgs,
    pollingInterval = 0,
  ): Observable<Flow[]> {
    return this.httpApiService
      .listFlowsForClient(args, pollingInterval)
      .pipe(map((res) => res.items?.map(translateFlow) ?? []));
  }

  listScheduledFlows(
    clientId: string,
    creator: string,
    pollingInterval = 0,
  ): Observable<ScheduledFlow[]> {
    return this.httpApiService
      .listScheduledFlows(clientId, creator, pollingInterval)
      .pipe(
        map((res) => res.scheduledFlows?.map(translateScheduledFlow) ?? []),
      );
  }

  listResultsForFlow(
    params: FlowResultsParams,
    pollingInterval = 0,
  ): Observable<ListFlowResultsResult> {
    return this.httpApiService
      .listResultsForFlow(params, pollingInterval)
      .pipe(map((res) => translateListFlowResultsResult(params.clientId, res)));
  }

  startFlow(
    clientId: string,
    flowName: string,
    flowArgs: apiInterfaces.Any,
    disableRrgSupport = false,
  ): Observable<Flow> {
    return this.httpApiService
      .startFlow(clientId, flowName, flowArgs, disableRrgSupport)
      .pipe(map((apiFlow) => translateFlow(apiFlow)));
  }

  scheduleFlow(
    clientId: string,
    flowName: string,
    flowArgs: apiInterfaces.Any,
  ): Observable<ScheduledFlow> {
    return this.httpApiService
      .scheduleFlow(clientId, flowName, flowArgs)
      .pipe(map((sf) => translateScheduledFlow(sf)));
  }

  cancelFlow(clientId: string, flowId: string): Observable<Flow> {
    return this.httpApiService
      .cancelFlow(clientId, flowId)
      .pipe(map((apiFlow) => translateFlow(apiFlow)));
  }

  unscheduleFlow(clientId: string, scheduledFlowId: string): Observable<{}> {
    return this.httpApiService.unscheduleFlow(clientId, scheduledFlowId);
  }

  fetchCurrentUser(): Observable<GrrUser> {
    return this.httpApiService
      .fetchCurrentUser()
      .pipe(map((user) => translateGrrUser(user)));
  }

  explainGlobExpression(
    clientId: string,
    globExpression: string,
    {exampleCount}: {exampleCount: number},
  ): Observable<GlobComponentExplanation[]> {
    return this.httpApiService
      .explainGlobExpression(clientId, globExpression, {
        exampleCount,
      })
      .pipe(
        map(
          (result) =>
            result.components?.map(translateGlobComponentExplanation) ?? [],
        ),
      );
  }

  fetchUiConfig(): Observable<UiConfig> {
    return this.httpApiService
      .fetchUiConfig()
      .pipe(map((uiConfig) => translateUiConfig(uiConfig)));
  }

  addClientLabel(clientId: string, label: string): Observable<{}> {
    return this.httpApiService.addClientLabel(clientId, label);
  }

  removeClientLabel(clientId: string, label: string): Observable<string> {
    return this.httpApiService
      .removeClientLabel(clientId, label)
      .pipe(mapTo(label));
  }

  fetchAllClientsLabels(): Observable<string[]> {
    return this.httpApiService
      .fetchAllClientsLabels()
      .pipe(map((labels) => labels.map(translateClientLabel)));
  }

  fetchClientSnapshots(
    clientId: string,
    start?: Date,
    end?: Date,
  ): Observable<ClientSnapshot[]> {
    return this.httpApiService
      .fetchClientSnapshots(clientId, start, end)
      .pipe(map((res) => res.snapshots?.map(translateClientSnapshot) ?? []));
  }

  fetchClientStartupInfos(
    clientId: string,
    start?: Date,
    end?: Date,
  ): Observable<StartupInfo[]> {
    return this.httpApiService
      .fetchClientStartupInfos(clientId, start, end)
      .pipe(
        map((res) => res.startupInfos?.map(translateClientStartupInfo) ?? []),
      );
  }

  suggestApprovers(usernameQuery: string): Observable<readonly string[]> {
    return this.httpApiService
      .suggestApprovers(usernameQuery)
      .pipe(map((res) => translateApproverSuggestions(res.suggestions ?? [])));
  }

  listRecentClientApprovals(parameters: {
    count?: number;
  }): Observable<readonly ClientApproval[]> {
    return this.httpApiService
      .listRecentClientApprovals(parameters)
      .pipe(map((res) => res.items?.map(translateClientApproval) ?? []));
  }

  getFileAccess(fileSpec: FileSpec): Observable<boolean> {
    return this.httpApiService.getFileAccess(fileSpec).pipe(
      map(() => true),
      catchError((err: HttpErrorResponse) => {
        if (err.status === 403) {
          return of(false);
        } else {
          return throwError(() => new Error(err.message));
        }
      }),
    );
  }

  getFileDetails(
    fileSpec: FileSpec,
    opts?: {timestamp?: Date},
  ): Observable<File | Directory> {
    return this.httpApiService
      .getFileDetails(fileSpec, opts)
      .pipe(map((apiFile) => translateFile(apiFile.file ?? {})));
  }

  getFileText(
    fileSpec: FileSpec,
    opts?: GetFileTextOptions,
  ): Observable<FileContent | null> {
    return this.httpApiService
      .getFileText(fileSpec, opts)
      .pipe(
        map((apiResult) =>
          apiResult ? translateApiGetFileTextResult(apiResult) : null,
        ),
      );
  }

  getFileBlobLength(
    fileSpec: FileSpec,
    opts?: GetFileBlobOptions,
  ): Observable<bigint | null> {
    return this.httpApiService.getFileBlobLength(fileSpec, opts);
  }

  getFileBlob(
    fileSpec: FileSpec,
    opts?: GetFileBlobOptions,
  ): Observable<ArrayBuffer | null> {
    return this.httpApiService.getFileBlob(fileSpec, opts);
  }

  browseFilesystem(
    clientId: string,
    path: string,
    opts: {includeDirectoryTree: boolean},
  ): Observable<BrowseFilesystemResult> {
    return this.httpApiService
      .browseFilesystem(clientId, path, opts)
      .pipe(map((res) => translateBrowseFilesystemResult(res)));
  }

  updateVfsFileContent(fileSpec: FileSpec): Observable<File | Directory> {
    return this.httpApiService
      .updateVfsFileContent(fileSpec)
      .pipe(map((apiFile) => translateFile(apiFile.file ?? {})));
  }

  refreshVfsFolder(
    fileSpec: FileSpec,
    maxDepth?: number,
  ): Observable<BrowseFilesystemResult> {
    const opts: apiInterfaces.ApiCreateVfsRefreshOperationArgs = {
      maxDepth: maxDepth ? maxDepth.toString() : undefined,
    };
    return this.httpApiService
      .refreshVfsFolder(fileSpec, opts)
      .pipe(map((res) => translateBrowseFilesystemResult(res)));
  }

  listBinaries(includeMetadata: boolean): Observable<Binary[]> {
    return this.httpApiService
      .listBinaries(includeMetadata)
      .pipe(
        map((res) =>
          (res.items ?? []).map(safeTranslateBinary).filter((b) => b != null),
        ),
      );
  }
}
