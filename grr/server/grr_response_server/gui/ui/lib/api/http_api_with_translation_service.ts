import {Injectable} from '@angular/core';
import {Observable, throwError, timer} from 'rxjs';
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
  ListHuntLogsArgs,
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
  toApiListHuntLogsArgs,
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
    return this.httpApiService.searchClients(args).pipe(
      map((results) => results.items?.map(translateClient) ?? []),
      catchError((error) => {
        console.error('Response translation error in searchClients:', error);
        return throwError(() => error);
      }),
    );
  }

  fetchClient(id: string, pollingInterval = 0): Observable<Client> {
    return this.httpApiService.fetchClient(id, pollingInterval).pipe(
      map((apiClient) => translateClient(apiClient)),
      catchError((error) => {
        console.error('Response translation error in fetchClient:', error);
        return throwError(() => error);
      }),
    );
  }

  requestClientApproval(
    args: ClientApprovalRequest,
  ): Observable<ClientApproval> {
    return this.httpApiService.requestClientApproval(args).pipe(
      map((apiApproval) => translateClientApproval(apiApproval)),
      catchError((error) => {
        console.error(
          'Response translation error in requestClientApproval:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  fetchApprovalConfig(): Observable<ApprovalConfig> {
    return this.httpApiService.fetchApprovalConfig().pipe(
      // Replace empty string (protobuf default) with undefined.
      map((res) => (res.value?.['value'] as string) ?? undefined),
      map((optionalCcEmail) => ({optionalCcEmail})),
      catchError((error) => {
        console.error(
          'Response translation error in fetchApprovalConfig:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  fetchWebAuthType(): Observable<string> {
    return this.httpApiService.fetchWebAuthType().pipe(
      // Replace empty string (protobuf default) with undefined.
      map((res) => (res.value?.['value'] as string) ?? undefined),
      catchError((error) => {
        console.error('Response translation error in fetchWebAuthType:', error);
        return throwError(() => error);
      }),
    );
  }

  fetchExportCommandPrefix(): Observable<string> {
    return this.httpApiService.fetchExportCommandPrefix().pipe(
      // Replace empty string (protobuf default) with undefined.
      map((res) => (res.value?.['value'] as string) ?? undefined),
      catchError((error) => {
        console.error(
          'Response translation error in fetchExportCommandPrefix:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  listClientApprovals(
    clientId: string,
    pollingInterval = 0,
  ): Observable<ClientApproval[]> {
    return this.httpApiService
      .listClientApprovals(clientId, pollingInterval)
      .pipe(
        map((res) => res.items?.map(translateClientApproval) ?? []),
        catchError((error) => {
          console.error(
            'Response translation error in listClientApprovals:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  verifyClientAccess(clientId: string, poll = 0): Observable<boolean> {
    return timer(0, poll)
      .pipe(
        exhaustMap(() => this.httpApiService.verifyClientAccess(clientId)),
        catchError((error) => {
          console.error(
            'Response translation error in verifyClientAccess:',
            error,
          );
          return throwError(() => error);
        }),
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
      .pipe(
        map((apiApproval) => translateClientApproval(apiApproval)),
        catchError((error) => {
          console.error(
            'Response translation error in fetchClientApproval:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  fetchFlow(clientId: string, flowId: string): Observable<Flow> {
    return this.httpApiService.fetchFlow(clientId, flowId).pipe(
      map((apiFlow) => translateFlow(apiFlow)),
      catchError((error) => {
        console.error('Response translation error in fetchFlow:', error);
        return throwError(() => error);
      }),
    );
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
        catchError((error) => {
          console.error('Response translation error in pollFlow:', error);
          return throwError(() => error);
        }),
        takeWhile(
          (flow) =>
            flow.state !== FlowState.FINISHED && flow.state !== FlowState.ERROR,
          true,
        ),
        shareReplay({bufferSize: 1, refCount: true}),
      );
  }

  fetchFlowLogs(clientId: string, flowId: string): Observable<FlowLogs> {
    return this.httpApiService.fetchFlowLogs(clientId, flowId).pipe(
      map((apiFlowLogs) => translateFlowLogs(apiFlowLogs)),
      catchError((error) => {
        console.error('Response translation error in fetchFlowLogs:', error);
        return throwError(() => error);
      }),
    );
  }

  listAllFlowOutputPluginLogs(
    clientId: string,
    flowId: string,
  ): Observable<ListAllOutputPluginLogsResult> {
    return this.httpApiService
      .listAllFlowOutputPluginLogs(clientId, flowId)
      .pipe(
        map(translateListAllOutputPluginLogsResult),
        catchError((error) => {
          console.error(
            'Response translation error in listAllFlowOutputPluginLogs:',
            error,
          );
          return throwError(() => error);
        }),
      );
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
      .pipe(
        map((hunt) => translateHunt(hunt)),
        catchError((error) => {
          console.error('Response translation error in createHunt:', error);
          return throwError(() => error);
        }),
      );
  }

  requestHuntApproval(args: HuntApprovalRequest): Observable<HuntApproval> {
    return this.httpApiService.requestHuntApproval(args).pipe(
      map((huntApproval) => translateHuntApproval(huntApproval)),
      catchError((error) => {
        console.error(
          'Response translation error in requestHuntApproval:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  listHuntApprovals(
    huntId: string,
    pollingInterval = 0,
  ): Observable<HuntApproval[]> {
    return this.httpApiService.listHuntApprovals(huntId, pollingInterval).pipe(
      map((res) => res.items?.map(translateHuntApproval) ?? []),
      catchError((error) => {
        console.error(
          'Response translation error in listHuntApprovals:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  fetchHunt(id: string, pollingInterval = 0): Observable<Hunt> {
    return this.httpApiService.fetchHunt(id, pollingInterval).pipe(
      map((hunt) => translateHunt(hunt)),
      catchError((error) => {
        console.error('Response translation error in fetchHunt:', error);
        return throwError(() => error);
      }),
    );
  }

  verifyHuntAccess(huntId: string, poll = 0): Observable<boolean> {
    return timer(0, poll)
      .pipe(
        exhaustMap(() => this.httpApiService.verifyHuntAccess(huntId)),
        catchError((error) => {
          console.error(
            'Response translation error in verifyHuntAccess:',
            error,
          );
          return throwError(() => error);
        }),
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
      .pipe(
        map((huntApproval) => translateHuntApproval(huntApproval)),
        catchError((error) => {
          console.error(
            'Response translation error in fetchHuntApproval:',
            error,
          );
          return throwError(() => error);
        }),
      );
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
      .pipe(
        map((huntApproval) => translateHuntApproval(huntApproval)),
        catchError((error) => {
          console.error(
            'Response translation error in grantHuntApproval:',
            error,
          );
          return throwError(() => error);
        }),
      );
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
      .pipe(
        map((hunt) => translateHunt(hunt)),
        catchError((error) => {
          console.error('Response translation error in patchHunt:', error);
          return throwError(() => error);
        }),
      );
  }

  getHuntResultsByType(
    huntId: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiCountHuntResultsByTypeResult> {
    return this.httpApiService
      .getHuntResultsByType(huntId, pollingInterval)
      .pipe(
        catchError((error) => {
          console.error(
            'Response translation error in getHuntResultsByType:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  listResultsForHunt(
    params: ListHuntResultsArgs,
    pollingInterval = 0,
  ): Observable<ListHuntResultsResult> {
    return this.httpApiService
      .listResultsForHunt(toApiListHuntResultsArgs(params), pollingInterval)
      .pipe(
        map((res) => translateListHuntResultsResult(res)),
        catchError((error) => {
          console.error(
            'Response translation error in listResultsForHunt:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  listErrorsForHunt(
    params: ListHuntErrorsArgs,
    pollingInterval = 0,
  ): Observable<ListHuntErrorsResult> {
    return this.httpApiService
      .listErrorsForHunt(toApiListHuntErrorsArgs(params))
      .pipe(
        map((res) => translateListHuntErrorsResult(res)),
        catchError((error) => {
          console.error(
            'Response translation error in listErrorsForHunt:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  getHuntClientCompletionStats(
    args: apiInterfaces.ApiGetHuntClientCompletionStatsArgs,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiGetHuntClientCompletionStatsResult> {
    return this.httpApiService
      .getHuntClientCompletionStats(args, pollingInterval)
      .pipe(
        catchError((error) => {
          console.error(
            'Response translation error in getHuntClientCompletionStats:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  listHunts(
    args: ListHuntsArgs,
    pollingInterval = 0,
  ): Observable<ListHuntsResult> {
    return this.httpApiService
      .listHunts(toApiListHuntsArgs(args), pollingInterval)
      .pipe(
        map((res) => translateListHuntsResult(res)),
        catchError((error) => {
          console.error('Response translation error in listHunts:', error);
          return throwError(() => error);
        }),
      );
  }

  fetchHuntLogs(args: ListHuntLogsArgs): Observable<ListHuntLogsResult> {
    return this.httpApiService.fetchHuntLogs(toApiListHuntLogsArgs(args)).pipe(
      map((res) => translateListHuntLogsResult(res)),
      catchError((error) => {
        console.error('Response translation error in fetchHuntLogs:', error);
        return throwError(() => error);
      }),
    );
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
      .pipe(
        map((apiApproval) => translateClientApproval(apiApproval)),
        catchError((error) => {
          console.error(
            'Response translation error in grantClientApproval:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  listFlowDescriptors(): Observable<FlowDescriptor[]> {
    return this.httpApiService.listFlowDescriptors().pipe(
      map((apiDescriptors) => apiDescriptors.map(translateFlowDescriptor)),
      catchError((error) => {
        console.error(
          'Response translation error in listFlowDescriptors:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  getArtifactDescriptorMap(): Observable<ArtifactDescriptorMap> {
    return this.httpApiService.listArtifactDescriptors().pipe(
      map((res) => translateArtifactDescriptors(res.items ?? [])),
      catchError((error) => {
        console.error(
          'Response translation error in getArtifactDescriptorMap:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  uploadArtifact(artifact: string): Observable<{}> {
    return this.httpApiService.uploadArtifact(artifact);
  }

  deleteArtifact(artifactName: string): Observable<{}> {
    return this.httpApiService.deleteArtifact(artifactName);
  }

  listOutputPluginDescriptors(): Observable<OutputPluginDescriptor[]> {
    return this.httpApiService.listOutputPluginDescriptors().pipe(
      map((res) => res.map(translateOutputPluginDescriptor) ?? []),
      catchError((error) => {
        console.error(
          'Response translation error in listOutputPluginDescriptors:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  listFlowsForClient(
    args: apiInterfaces.ApiListFlowsArgs,
    pollingInterval = 0,
  ): Observable<Flow[]> {
    return this.httpApiService.listFlowsForClient(args, pollingInterval).pipe(
      map((res) => res.items?.map(translateFlow) ?? []),
      catchError((error) => {
        console.error(
          'Response translation error in listFlowsForClient:',
          error,
        );
        return throwError(() => error);
      }),
    );
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
        catchError((error) => {
          console.error(
            'Response translation error in listScheduledFlows:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  listResultsForFlow(
    params: FlowResultsParams,
    pollingInterval = 0,
  ): Observable<ListFlowResultsResult> {
    return this.httpApiService.listResultsForFlow(params, pollingInterval).pipe(
      map((res) => translateListFlowResultsResult(params.clientId, res)),
      catchError((error) => {
        console.error(
          'Response translation error in listResultsForFlow:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  startFlow(
    clientId: string,
    flowName: string,
    flowArgs: apiInterfaces.Any,
    disableRrgSupport = false,
  ): Observable<Flow> {
    return this.httpApiService
      .startFlow(clientId, flowName, flowArgs, disableRrgSupport)
      .pipe(
        map((apiFlow) => translateFlow(apiFlow)),
        catchError((error) => {
          console.error('Response translation error in startFlow:', error);
          return throwError(() => error);
        }),
      );
  }

  scheduleFlow(
    clientId: string,
    flowName: string,
    flowArgs: apiInterfaces.Any,
  ): Observable<ScheduledFlow> {
    return this.httpApiService.scheduleFlow(clientId, flowName, flowArgs).pipe(
      map((sf) => translateScheduledFlow(sf)),
      catchError((error) => {
        console.error('Response translation error in scheduleFlow:', error);
        return throwError(() => error);
      }),
    );
  }

  cancelFlow(clientId: string, flowId: string): Observable<Flow> {
    return this.httpApiService.cancelFlow(clientId, flowId).pipe(
      map((apiFlow) => translateFlow(apiFlow)),
      catchError((error) => {
        console.error('Response translation error in cancelFlow:', error);
        return throwError(() => error);
      }),
    );
  }

  unscheduleFlow(clientId: string, scheduledFlowId: string): Observable<{}> {
    return this.httpApiService.unscheduleFlow(clientId, scheduledFlowId);
  }

  fetchCurrentUser(): Observable<GrrUser> {
    return this.httpApiService.fetchCurrentUser().pipe(
      map((user) => translateGrrUser(user)),
      catchError((error) => {
        console.error('Response translation error in fetchCurrentUser:', error);
        return throwError(() => error);
      }),
    );
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
        catchError((error) => {
          console.error(
            'Response translation error in explainGlobExpression:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  fetchUiConfig(): Observable<UiConfig> {
    return this.httpApiService.fetchUiConfig().pipe(
      map((uiConfig) => translateUiConfig(uiConfig)),
      catchError((error) => {
        console.error('Response translation error in fetchUiConfig:', error);
        return throwError(() => error);
      }),
    );
  }

  addClientLabel(clientId: string, label: string): Observable<{}> {
    return this.httpApiService.addClientLabel(clientId, label);
  }

  removeClientLabel(clientId: string, label: string): Observable<string> {
    return this.httpApiService.removeClientLabel(clientId, label).pipe(
      mapTo(label),
      catchError((error) => {
        console.error(
          'Response translation error in removeClientLabel:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  fetchAllClientsLabels(): Observable<string[]> {
    return this.httpApiService.fetchAllClientsLabels().pipe(
      map((labels) => labels.map(translateClientLabel)),
      catchError((error) => {
        console.error(
          'Response translation error in fetchAllClientsLabels:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  fetchClientSnapshots(
    clientId: string,
    start?: Date,
    end?: Date,
  ): Observable<ClientSnapshot[]> {
    return this.httpApiService.fetchClientSnapshots(clientId, start, end).pipe(
      map((res) => res.snapshots?.map(translateClientSnapshot) ?? []),
      catchError((error) => {
        console.error(
          'Response translation error in fetchClientSnapshots:',
          error,
        );
        return throwError(() => error);
      }),
    );
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
        catchError((error) => {
          console.error(
            'Response translation error in fetchClientStartupInfos:',
            error,
          );
          return throwError(() => error);
        }),
      );
  }

  suggestApprovers(usernameQuery: string): Observable<readonly string[]> {
    return this.httpApiService.suggestApprovers(usernameQuery).pipe(
      map((res) => translateApproverSuggestions(res.suggestions ?? [])),
      catchError((error) => {
        console.error('Response translation error in suggestApprovers:', error);
        return throwError(() => error);
      }),
    );
  }

  listRecentClientApprovals(parameters: {
    count?: number;
  }): Observable<readonly ClientApproval[]> {
    return this.httpApiService.listRecentClientApprovals(parameters).pipe(
      map((res) => res.items?.map(translateClientApproval) ?? []),
      catchError((error) => {
        console.error(
          'Response translation error in listRecentClientApprovals:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  getFileAccess(fileSpec: FileSpec): Observable<boolean> {
    return this.httpApiService.getFileAccess(fileSpec);
  }

  getFileDetails(
    fileSpec: FileSpec,
    opts?: {timestamp?: Date},
  ): Observable<File | Directory> {
    return this.httpApiService.getFileDetails(fileSpec, opts).pipe(
      map((apiFile) => translateFile(apiFile.file ?? {})),
      catchError((error) => {
        console.error('Response translation error in getFileDetails:', error);
        return throwError(() => error);
      }),
    );
  }

  getFileText(
    fileSpec: FileSpec,
    opts?: GetFileTextOptions,
  ): Observable<FileContent | null> {
    return this.httpApiService.getFileText(fileSpec, opts).pipe(
      map((apiResult) =>
        apiResult ? translateApiGetFileTextResult(apiResult) : null,
      ),
      catchError((error) => {
        console.error('Response translation error in getFileText:', error);
        return throwError(() => error);
      }),
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
    return this.httpApiService.browseFilesystem(clientId, path, opts).pipe(
      map((res) => translateBrowseFilesystemResult(res)),
      catchError((error) => {
        console.error('Response translation error in browseFilesystem:', error);
        return throwError(() => error);
      }),
    );
  }

  updateVfsFileContent(fileSpec: FileSpec): Observable<File | Directory> {
    return this.httpApiService.updateVfsFileContent(fileSpec).pipe(
      map((apiFile) => translateFile(apiFile.file ?? {})),
      catchError((error) => {
        console.error(
          'Response translation error in updateVfsFileContent:',
          error,
        );
        return throwError(() => error);
      }),
    );
  }

  refreshVfsFolder(
    fileSpec: FileSpec,
    maxDepth?: number,
  ): Observable<BrowseFilesystemResult> {
    const opts: apiInterfaces.ApiCreateVfsRefreshOperationArgs = {
      maxDepth: maxDepth ? maxDepth.toString() : undefined,
    };
    return this.httpApiService.refreshVfsFolder(fileSpec, opts).pipe(
      map((res) => translateBrowseFilesystemResult(res)),
      catchError((error) => {
        console.error('Response translation error in refreshVfsFolder:', error);
        return throwError(() => error);
      }),
    );
  }

  listBinaries(includeMetadata: boolean): Observable<Binary[]> {
    return this.httpApiService.listBinaries(includeMetadata).pipe(
      map((res) =>
        (res.items ?? []).map(safeTranslateBinary).filter((b) => b != null),
      ),
      catchError((error) => {
        console.error('Response translation error in listBinaries:', error);
        return throwError(() => error);
      }),
    );
  }
}
