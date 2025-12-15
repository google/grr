/**
 * @fileoverview The module provides mappings for GRR API protos
 * (in JSON format) to TypeScript interfaces. This file is generated
 * from the OpenAPI description.
 * g3-prettier-ignore-file
 */



/** BinaryStream proto mapping. */
export type BinaryStream = string;

/** ByteSize proto mapping. */
export type ByteSize = string;

/** Duration proto mapping. */
export type Duration = string;

/** DurationSeconds proto mapping. */
export type DurationSeconds = string;

/** GlobExpression proto mapping. */
export type GlobExpression = string;

/** HashDigest proto mapping. */
export type HashDigest = string;

/** RDFBytes proto mapping. */
export type RDFBytes = string;

/** RDFDatetime proto mapping. */
export type RDFDatetime = string;

/** RDFDatetimeSeconds proto mapping. */
export type RDFDatetimeSeconds = string;

/** RDFURN proto mapping. */
export type RDFURN = string;

/** SessionID proto mapping. */
export type SessionID = string;

/** google.protobuf.Any proto mapping. */
export declare interface Any {
  readonly '@type'?: string;
  readonly [key: string]: undefined|null|string|number|boolean|object;
}

/** AdminUIClientWarningRule proto mapping. */
export declare interface AdminUIClientWarningRule {
  readonly withLabels?: readonly string[];
  readonly message?: string;
}

/** AdminUIClientWarningsConfigOption proto mapping. */
export declare interface AdminUIClientWarningsConfigOption {
  readonly rules?: readonly AdminUIClientWarningRule[];
}

/** AdminUIHuntConfig proto mapping. */
export declare interface AdminUIHuntConfig {
  readonly defaultIncludeLabels?: readonly string[];
  readonly defaultExcludeLabels?: readonly string[];
  readonly presubmitCheckWithSkipTag?: string;
  readonly presubmitWarningMessage?: string;
}

/** AmazonCloudInstance proto mapping. */
export declare interface AmazonCloudInstance {
  readonly instanceId?: string;
  readonly amiId?: string;
  readonly hostname?: string;
  readonly publicHostname?: string;
  readonly instanceType?: string;
}

/** ApiAddClientsLabelsArgs proto mapping. */
export declare interface ApiAddClientsLabelsArgs {
  readonly clientIds?: readonly string[];
  readonly labels?: readonly string[];
}

/** ApiAff4ObjectAttribute proto mapping. */
export declare interface ApiAff4ObjectAttribute {
  readonly name?: string;
  readonly values?: readonly ApiAff4ObjectAttributeValue[];
}

/** ApiAff4ObjectAttributeValue proto mapping. */
export declare interface ApiAff4ObjectAttributeValue {
  readonly type?: string;
  readonly age?: RDFDatetime;
  readonly value?: Any;
}

/** ApiAff4ObjectRepresentation proto mapping. */
export declare interface ApiAff4ObjectRepresentation {
  readonly types?: readonly ApiAff4ObjectType[];
}

/** ApiAff4ObjectType proto mapping. */
export declare interface ApiAff4ObjectType {
  readonly name?: string;
  readonly attributes?: readonly ApiAff4ObjectAttribute[];
}

/** ApiBrowseFilesystemArgs proto mapping. */
export declare interface ApiBrowseFilesystemArgs {
  readonly clientId?: string;
  readonly path?: string;
  readonly includeDirectoryTree?: boolean;
  readonly timestamp?: RDFDatetime;
}

/** ApiBrowseFilesystemEntry proto mapping. */
export declare interface ApiBrowseFilesystemEntry {
  readonly file?: ApiFile;
  readonly children?: readonly ApiBrowseFilesystemEntry[];
}

/** ApiBrowseFilesystemResult proto mapping. */
export declare interface ApiBrowseFilesystemResult {
  readonly rootEntry?: ApiBrowseFilesystemEntry;
}

/** ApiCancelFlowArgs proto mapping. */
export declare interface ApiCancelFlowArgs {
  readonly clientId?: string;
  readonly flowId?: string;
}

/** ApiClient proto mapping. */
export declare interface ApiClient {
  readonly clientId?: string;
  readonly urn?: string;
  readonly agentInfo?: ClientInformation;
  readonly hardwareInfo?: HardwareInfo;
  readonly osInfo?: Uname;
  readonly knowledgeBase?: KnowledgeBase;
  readonly memorySize?: ByteSize;
  readonly firstSeenAt?: RDFDatetime;
  readonly lastSeenAt?: RDFDatetime;
  readonly lastBootedAt?: RDFDatetime;
  readonly lastClock?: RDFDatetime;
  readonly lastCrashAt?: RDFDatetime;
  readonly labels?: readonly ClientLabel[];
  readonly interfaces?: readonly Interface[];
  readonly volumes?: readonly Volume[];
  readonly age?: RDFDatetime;
  readonly cloudInstance?: CloudInstance;
  readonly sourceFlowId?: string;
  readonly rrgVersion?: string;
  readonly rrgArgs?: readonly string[];
}

/** ApiClientApproval proto mapping. */
export declare interface ApiClientApproval {
  readonly subject?: ApiClient;
  readonly id?: string;
  readonly requestor?: string;
  readonly reason?: string;
  readonly isValid?: boolean;
  readonly isValidMessage?: string;
  readonly emailMessageId?: string;
  readonly notifiedUsers?: readonly string[];
  readonly emailCcAddresses?: readonly string[];
  readonly approvers?: readonly string[];
  readonly expirationTimeUs?: RDFDatetime;
}

/** ApiConfigOption proto mapping. */
export declare interface ApiConfigOption {
  readonly name?: string;
  readonly isRedacted?: boolean;
  readonly value?: Any;
  readonly type?: string;
  readonly isInvalid?: boolean;
}

/** ApiConfigSection proto mapping. */
export declare interface ApiConfigSection {
  readonly name?: string;
  readonly options?: readonly ApiConfigOption[];
}

/** ApiCountHuntResultsByTypeArgs proto mapping. */
export declare interface ApiCountHuntResultsByTypeArgs {
  readonly huntId?: string;
}

/** ApiCountHuntResultsByTypeResult proto mapping. */
export declare interface ApiCountHuntResultsByTypeResult {
  readonly items?: readonly ApiTypeCount[];
}

/** ApiCreateClientApprovalArgs proto mapping. */
export declare interface ApiCreateClientApprovalArgs {
  readonly clientId?: string;
  readonly approval?: ApiClientApproval;
}

/** ApiCreateCronJobApprovalArgs proto mapping. */
export declare interface ApiCreateCronJobApprovalArgs {
  readonly cronJobId?: string;
  readonly approval?: ApiCronJobApproval;
}

/** ApiCreateCronJobArgs proto mapping. */
export declare interface ApiCreateCronJobArgs {
  readonly flowName?: string;
  readonly flowArgs?: Any;
  readonly huntRunnerArgs?: HuntRunnerArgs;
  readonly description?: string;
  readonly periodicity?: DurationSeconds;
  readonly lifetime?: DurationSeconds;
  readonly allowOverruns?: boolean;
}

/** ApiCreateFlowArgs proto mapping. */
export declare interface ApiCreateFlowArgs {
  readonly clientId?: string;
  readonly flow?: ApiFlow;
  readonly originalFlow?: ApiFlowReference;
}

/** ApiCreateHuntApprovalArgs proto mapping. */
export declare interface ApiCreateHuntApprovalArgs {
  readonly huntId?: string;
  readonly approval?: ApiHuntApproval;
}

/** ApiCreateHuntArgs proto mapping. */
export declare interface ApiCreateHuntArgs {
  readonly flowName?: string;
  readonly flowArgs?: Any;
  readonly huntRunnerArgs?: HuntRunnerArgs;
  readonly originalFlow?: ApiFlowReference;
  readonly originalHunt?: ApiHuntReference;
}

/** ApiCreateVfsRefreshOperationArgs proto mapping. */
export declare interface ApiCreateVfsRefreshOperationArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly maxDepth?: ProtoUint64;
  readonly notifyUser?: boolean;
}

/** ApiCreateVfsRefreshOperationResult proto mapping. */
export declare interface ApiCreateVfsRefreshOperationResult {
  readonly operationId?: string;
}

/** ApiCronJob proto mapping. */
export declare interface ApiCronJob {
  readonly cronJobId?: string;
  readonly args?: CronJobAction;
  readonly createdAt?: RDFDatetime;
  readonly currentRunId?: string;
  readonly enabled?: boolean;
  readonly lastRunStatus?: CronJobRunCronJobRunStatus;
  readonly lastRunTime?: RDFDatetime;
  readonly state?: ApiDataObject;
  readonly frequency?: DurationSeconds;
  readonly lifetime?: DurationSeconds;
  readonly allowOverruns?: boolean;
  readonly forcedRunRequested?: boolean;
  readonly isFailing?: boolean;
  readonly description?: string;
}

/** ApiCronJobApproval proto mapping. */
export declare interface ApiCronJobApproval {
  readonly subject?: ApiCronJob;
  readonly id?: string;
  readonly requestor?: string;
  readonly reason?: string;
  readonly isValid?: boolean;
  readonly isValidMessage?: string;
  readonly emailMessageId?: string;
  readonly notifiedUsers?: readonly string[];
  readonly emailCcAddresses?: readonly string[];
  readonly approvers?: readonly string[];
}

/** ApiCronJobRun proto mapping. */
export declare interface ApiCronJobRun {
  readonly runId?: string;
  readonly cronJobId?: string;
  readonly startedAt?: RDFDatetime;
  readonly finishedAt?: RDFDatetime;
  readonly status?: CronJobRunCronJobRunStatus;
  readonly logMessage?: string;
  readonly backtrace?: string;
}

/** ApiDataObject proto mapping. */
export declare interface ApiDataObject {
  readonly items?: readonly ApiDataObjectKeyValuePair[];
}

/** ApiDataObjectKeyValuePair proto mapping. */
export declare interface ApiDataObjectKeyValuePair {
  readonly key?: string;
  readonly value?: Any;
  readonly invalid?: boolean;
  readonly type?: string;
}

/** ApiDeleteArtifactsArgs proto mapping. */
export declare interface ApiDeleteArtifactsArgs {
  readonly names?: readonly string[];
}

/** ApiDeleteCronJobArgs proto mapping. */
export declare interface ApiDeleteCronJobArgs {
  readonly cronJobId?: string;
}

/** ApiDeleteFleetspeakPendingMessagesArgs proto mapping. */
export declare interface ApiDeleteFleetspeakPendingMessagesArgs {
  readonly clientId?: string;
}

/** ApiDeleteHuntArgs proto mapping. */
export declare interface ApiDeleteHuntArgs {
  readonly huntId?: string;
}

/** ApiDeletePendingUserNotificationArgs proto mapping. */
export declare interface ApiDeletePendingUserNotificationArgs {
  readonly timestamp?: RDFDatetime;
}

/** ApiExplainGlobExpressionArgs proto mapping. */
export declare interface ApiExplainGlobExpressionArgs {
  readonly globExpression?: string;
  readonly exampleCount?: ProtoUint32;
  readonly clientId?: string;
}

/** ApiExplainGlobExpressionResult proto mapping. */
export declare interface ApiExplainGlobExpressionResult {
  readonly components?: readonly GlobComponentExplanation[];
}

/** ApiFile proto mapping. */
export declare interface ApiFile {
  readonly name?: string;
  readonly path?: string;
  readonly type?: string;
  readonly stat?: StatEntry;
  readonly age?: RDFDatetime;
  readonly isDirectory?: boolean;
  readonly hash?: Hash;
  readonly lastCollected?: RDFDatetime;
  readonly lastCollectedSize?: ProtoUint64;
  readonly details?: ApiAff4ObjectRepresentation;
}

/** ApiFleetspeakAddress proto mapping. */
export declare interface ApiFleetspeakAddress {
  readonly clientId?: string;
  readonly serviceName?: string;
}

/** ApiFleetspeakAnnotations proto mapping. */
export declare interface ApiFleetspeakAnnotations {
  readonly entries?: readonly ApiFleetspeakAnnotationsEntry[];
}

/** ApiFleetspeakAnnotations.Entry proto mapping. */
export declare interface ApiFleetspeakAnnotationsEntry {
  readonly key?: string;
  readonly value?: string;
}

/** ApiFleetspeakMessage proto mapping. */
export declare interface ApiFleetspeakMessage {
  readonly messageId?: ProtoBytes;
  readonly source?: ApiFleetspeakAddress;
  readonly sourceMessageId?: ProtoBytes;
  readonly destination?: ApiFleetspeakAddress;
  readonly messageType?: string;
  readonly creationTime?: RDFDatetime;
  readonly data?: Any;
  readonly validationInfo?: ApiFleetspeakValidationInfo;
  readonly result?: ApiFleetspeakMessageResult;
  readonly priority?: ApiFleetspeakMessagePriority;
  readonly background?: boolean;
  readonly annotations?: ApiFleetspeakAnnotations;
}

/** ApiFleetspeakMessage.Priority proto mapping. */
export enum ApiFleetspeakMessagePriority {
  MEDIUM = 'MEDIUM',
  LOW = 'LOW',
  HIGH = 'HIGH',
}

/** ApiFleetspeakMessageResult proto mapping. */
export declare interface ApiFleetspeakMessageResult {
  readonly processedTime?: RDFDatetime;
  readonly failed?: boolean;
  readonly failedReason?: string;
}

/** ApiFleetspeakValidationInfo proto mapping. */
export declare interface ApiFleetspeakValidationInfo {
  readonly tags?: readonly ApiFleetspeakValidationInfoTag[];
}

/** ApiFleetspeakValidationInfo.Tag proto mapping. */
export declare interface ApiFleetspeakValidationInfoTag {
  readonly key?: string;
  readonly value?: string;
}

/** ApiFlow proto mapping. */
export declare interface ApiFlow {
  readonly urn?: SessionID;
  readonly flowId?: string;
  readonly clientId?: string;
  readonly name?: string;
  readonly args?: Any;
  readonly progress?: Any;
  readonly resultMetadata?: FlowResultMetadata;
  readonly runnerArgs?: FlowRunnerArgs;
  readonly state?: ApiFlowState;
  readonly errorDescription?: string;
  readonly startedAt?: RDFDatetime;
  readonly lastActiveAt?: RDFDatetime;
  readonly creator?: string;
  readonly isRobot?: boolean;
  readonly stateData?: ApiDataObject;
  readonly store?: Any;
  readonly context?: FlowContext;
  readonly nestedFlows?: readonly ApiFlow[];
  readonly originalFlow?: ApiFlowReference;
  readonly internalError?: string;
}

/** ApiFlow.State proto mapping. */
export enum ApiFlowState {
  RUNNING = 'RUNNING',
  TERMINATED = 'TERMINATED',
  ERROR = 'ERROR',
  CLIENT_CRASHED = 'CLIENT_CRASHED',
}

/** ApiFlowDescriptor proto mapping. */
export declare interface ApiFlowDescriptor {
  readonly name?: string;
  readonly friendlyName?: string;
  readonly category?: string;
  readonly doc?: string;
  readonly argsType?: string;
  readonly defaultArgs?: Any;
  readonly behaviours?: readonly string[];
  readonly blockHuntCreation?: boolean;
}

/** ApiFlowLikeObjectReference proto mapping. */
export declare interface ApiFlowLikeObjectReference {
  readonly objectType?: ApiFlowLikeObjectReferenceObjectType;
  readonly flowReference?: ApiFlowReference;
  readonly huntReference?: ApiHuntReference;
}

/** ApiFlowLikeObjectReference.ObjectType proto mapping. */
export enum ApiFlowLikeObjectReferenceObjectType {
  UNKNOWN = 'UNKNOWN',
  FLOW_REFERENCE = 'FLOW_REFERENCE',
  HUNT_REFERENCE = 'HUNT_REFERENCE',
}

/** ApiFlowLog proto mapping. */
export declare interface ApiFlowLog {
  readonly logMessage?: string;
  readonly flowName?: string;
  readonly flowId?: string;
  readonly timestamp?: RDFDatetime;
}

/** ApiFlowReference proto mapping. */
export declare interface ApiFlowReference {
  readonly flowId?: string;
  readonly clientId?: string;
}

/** ApiFlowRequest proto mapping. */
export declare interface ApiFlowRequest {
  readonly requestId?: string;
  readonly requestState?: RequestState;
  readonly responses?: readonly GrrMessage[];
}

/** ApiFlowResult proto mapping. */
export declare interface ApiFlowResult {
  readonly payload?: Any;
  readonly timestamp?: RDFDatetime;
  readonly tag?: string;
}

/** ApiForceRunCronJobArgs proto mapping. */
export declare interface ApiForceRunCronJobArgs {
  readonly cronJobId?: string;
}

/** ApiGetClientApprovalArgs proto mapping. */
export declare interface ApiGetClientApprovalArgs {
  readonly clientId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiGetClientArgs proto mapping. */
export declare interface ApiGetClientArgs {
  readonly clientId?: string;
  readonly timestamp?: RDFDatetime;
}

/** ApiGetClientSnapshotsArgs proto mapping. */
export declare interface ApiGetClientSnapshotsArgs {
  readonly clientId?: string;
  readonly start?: RDFDatetime;
  readonly end?: RDFDatetime;
}

/** ApiGetClientSnapshotsResult proto mapping. */
export declare interface ApiGetClientSnapshotsResult {
  readonly snapshots?: readonly ClientSnapshot[];
}

/** ApiGetClientStartupInfosArgs proto mapping. */
export declare interface ApiGetClientStartupInfosArgs {
  readonly clientId?: string;
  readonly start?: RDFDatetime;
  readonly end?: RDFDatetime;
  readonly excludeSnapshotCollections?: boolean;
}

/** ApiGetClientStartupInfosResult proto mapping. */
export declare interface ApiGetClientStartupInfosResult {
  readonly startupInfos?: readonly StartupInfo[];
}

/** ApiGetClientVersionTimesArgs proto mapping. */
export declare interface ApiGetClientVersionTimesArgs {
  readonly clientId?: string;
}

/** ApiGetClientVersionTimesResult proto mapping. */
export declare interface ApiGetClientVersionTimesResult {
  readonly times?: readonly RDFDatetime[];
}

/** ApiGetClientVersionsArgs proto mapping. */
export declare interface ApiGetClientVersionsArgs {
  readonly clientId?: string;
  readonly start?: RDFDatetime;
  readonly end?: RDFDatetime;
  readonly mode?: ApiGetClientVersionsArgsMode;
}

/** ApiGetClientVersionsArgs.Mode proto mapping. */
export enum ApiGetClientVersionsArgsMode {
  UNSET = 'UNSET',
  FULL = 'FULL',
  DIFF = 'DIFF',
}

/** ApiGetClientVersionsResult proto mapping. */
export declare interface ApiGetClientVersionsResult {
  readonly items?: readonly ApiClient[];
}

/** ApiGetCollectedHuntTimelinesArgs proto mapping. */
export declare interface ApiGetCollectedHuntTimelinesArgs {
  readonly huntId?: string;
  readonly format?: ApiGetCollectedTimelineArgsFormat;
  readonly bodyOpts?: ApiTimelineBodyOpts;
}

/** ApiGetCollectedTimelineArgs proto mapping. */
export declare interface ApiGetCollectedTimelineArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly format?: ApiGetCollectedTimelineArgsFormat;
  readonly bodyOpts?: ApiTimelineBodyOpts;
}

/** ApiGetCollectedTimelineArgs.Format proto mapping. */
export enum ApiGetCollectedTimelineArgsFormat {
  UNSPECIFIED = 'UNSPECIFIED',
  BODY = 'BODY',
  RAW_GZCHUNKED = 'RAW_GZCHUNKED',
}

/** ApiGetConfigOptionArgs proto mapping. */
export declare interface ApiGetConfigOptionArgs {
  readonly name?: string;
}

/** ApiGetConfigResult proto mapping. */
export declare interface ApiGetConfigResult {
  readonly sections?: readonly ApiConfigSection[];
}

/** ApiGetCronJobApprovalArgs proto mapping. */
export declare interface ApiGetCronJobApprovalArgs {
  readonly cronJobId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiGetCronJobArgs proto mapping. */
export declare interface ApiGetCronJobArgs {
  readonly cronJobId?: string;
}

/** ApiGetCronJobRunArgs proto mapping. */
export declare interface ApiGetCronJobRunArgs {
  readonly cronJobId?: string;
  readonly runId?: string;
}

/** ApiGetExportedFlowResultsArgs proto mapping. */
export declare interface ApiGetExportedFlowResultsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly pluginName?: string;
}

/** ApiGetExportedHuntResultsArgs proto mapping. */
export declare interface ApiGetExportedHuntResultsArgs {
  readonly huntId?: string;
  readonly pluginName?: string;
}

/** ApiGetFileBlobArgs proto mapping. */
export declare interface ApiGetFileBlobArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly offset?: ProtoInt64;
  readonly length?: ProtoInt64;
  readonly timestamp?: RDFDatetime;
}

/** ApiGetFileDetailsArgs proto mapping. */
export declare interface ApiGetFileDetailsArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly timestamp?: RDFDatetime;
}

/** ApiGetFileDetailsResult proto mapping. */
export declare interface ApiGetFileDetailsResult {
  readonly file?: ApiFile;
}

/** ApiGetFileDownloadCommandArgs proto mapping. */
export declare interface ApiGetFileDownloadCommandArgs {
  readonly clientId?: string;
  readonly filePath?: string;
}

/** ApiGetFileDownloadCommandResult proto mapping. */
export declare interface ApiGetFileDownloadCommandResult {
  readonly command?: string;
}

/** ApiGetFileTextArgs proto mapping. */
export declare interface ApiGetFileTextArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly offset?: ProtoInt64;
  readonly length?: ProtoInt64;
  readonly encoding?: ApiGetFileTextArgsEncoding;
  readonly timestamp?: RDFDatetime;
}

/** ApiGetFileTextArgs.Encoding proto mapping. */
export enum ApiGetFileTextArgsEncoding {
  BASE64_CODEC = 'BASE64_CODEC',
  BIG5 = 'BIG5',
  BIG5HKSCS = 'BIG5HKSCS',
  CP037 = 'CP037',
  CP1006 = 'CP1006',
  CP1026 = 'CP1026',
  CP1140 = 'CP1140',
  CP1250 = 'CP1250',
  CP1251 = 'CP1251',
  CP1252 = 'CP1252',
  CP1253 = 'CP1253',
  CP1254 = 'CP1254',
  CP1255 = 'CP1255',
  CP1256 = 'CP1256',
  CP1257 = 'CP1257',
  CP1258 = 'CP1258',
  CP424 = 'CP424',
  CP437 = 'CP437',
  CP500 = 'CP500',
  CP737 = 'CP737',
  CP775 = 'CP775',
  CP850 = 'CP850',
  CP852 = 'CP852',
  CP855 = 'CP855',
  CP856 = 'CP856',
  CP857 = 'CP857',
  CP860 = 'CP860',
  CP861 = 'CP861',
  CP862 = 'CP862',
  CP863 = 'CP863',
  CP864 = 'CP864',
  CP865 = 'CP865',
  CP866 = 'CP866',
  CP869 = 'CP869',
  CP874 = 'CP874',
  CP875 = 'CP875',
  CP932 = 'CP932',
  CP949 = 'CP949',
  CP950 = 'CP950',
  IDNA = 'IDNA',
  ROT_13 = 'ROT_13',
  UTF_16 = 'UTF_16',
  UTF_16_BE = 'UTF_16_BE',
  UTF_16_LE = 'UTF_16_LE',
  UTF_32 = 'UTF_32',
  UTF_32_BE = 'UTF_32_BE',
  UTF_32_LE = 'UTF_32_LE',
  UTF_7 = 'UTF_7',
  UTF_8 = 'UTF_8',
  UTF_8_SIG = 'UTF_8_SIG',
  UU_CODEC = 'UU_CODEC',
  ZLIB_CODEC = 'ZLIB_CODEC',
}

/** ApiGetFileTextResult proto mapping. */
export declare interface ApiGetFileTextResult {
  readonly content?: string;
  readonly totalSize?: ProtoInt64;
}

/** ApiGetFileVersionTimesArgs proto mapping. */
export declare interface ApiGetFileVersionTimesArgs {
  readonly clientId?: string;
  readonly filePath?: string;
}

/** ApiGetFileVersionTimesResult proto mapping. */
export declare interface ApiGetFileVersionTimesResult {
  readonly times?: readonly RDFDatetime[];
}

/** ApiGetFleetspeakPendingMessageCountArgs proto mapping. */
export declare interface ApiGetFleetspeakPendingMessageCountArgs {
  readonly clientId?: string;
}

/** ApiGetFleetspeakPendingMessageCountResult proto mapping. */
export declare interface ApiGetFleetspeakPendingMessageCountResult {
  readonly count?: ProtoUint64;
}

/** ApiGetFleetspeakPendingMessagesArgs proto mapping. */
export declare interface ApiGetFleetspeakPendingMessagesArgs {
  readonly clientId?: string;
  readonly offset?: ProtoUint64;
  readonly limit?: ProtoUint64;
  readonly wantData?: boolean;
}

/** ApiGetFleetspeakPendingMessagesResult proto mapping. */
export declare interface ApiGetFleetspeakPendingMessagesResult {
  readonly messages?: readonly ApiFleetspeakMessage[];
}

/** ApiGetFlowArgs proto mapping. */
export declare interface ApiGetFlowArgs {
  readonly clientId?: string;
  readonly flowId?: string;
}

/** ApiGetFlowFilesArchiveArgs proto mapping. */
export declare interface ApiGetFlowFilesArchiveArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly archiveFormat?: ApiGetFlowFilesArchiveArgsArchiveFormat;
}

/** ApiGetFlowFilesArchiveArgs.ArchiveFormat proto mapping. */
export enum ApiGetFlowFilesArchiveArgsArchiveFormat {
  ZIP = 'ZIP',
  TAR_GZ = 'TAR_GZ',
}

/** ApiGetFlowResultsExportCommandArgs proto mapping. */
export declare interface ApiGetFlowResultsExportCommandArgs {
  readonly clientId?: string;
  readonly flowId?: string;
}

/** ApiGetFlowResultsExportCommandResult proto mapping. */
export declare interface ApiGetFlowResultsExportCommandResult {
  readonly command?: string;
}

/** ApiGetGrrBinaryArgs proto mapping. */
export declare interface ApiGetGrrBinaryArgs {
  readonly type?: ApiGrrBinaryType;
  readonly path?: string;
}

/** ApiGetGrrBinaryBlobArgs proto mapping. */
export declare interface ApiGetGrrBinaryBlobArgs {
  readonly type?: ApiGrrBinaryType;
  readonly path?: string;
}

/** ApiGetGrrVersionResult proto mapping. */
export declare interface ApiGetGrrVersionResult {
  readonly major?: ProtoUint32;
  readonly minor?: ProtoUint32;
  readonly revision?: ProtoUint32;
  readonly release?: ProtoUint32;
}

/** ApiGetHuntApprovalArgs proto mapping. */
export declare interface ApiGetHuntApprovalArgs {
  readonly huntId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiGetHuntArgs proto mapping. */
export declare interface ApiGetHuntArgs {
  readonly huntId?: string;
}

/** ApiGetHuntClientCompletionStatsArgs proto mapping. */
export declare interface ApiGetHuntClientCompletionStatsArgs {
  readonly huntId?: string;
  readonly size?: ProtoInt64;
}

/** ApiGetHuntClientCompletionStatsResult proto mapping. */
export declare interface ApiGetHuntClientCompletionStatsResult {
  readonly startPoints?: readonly SampleFloat[];
  readonly completePoints?: readonly SampleFloat[];
}

/** ApiGetHuntContextArgs proto mapping. */
export declare interface ApiGetHuntContextArgs {
  readonly huntId?: string;
}

/** ApiGetHuntContextResult proto mapping. */
export declare interface ApiGetHuntContextResult {
  readonly context?: HuntContext;
  readonly state?: ApiDataObject;
}

/** ApiGetHuntFileArgs proto mapping. */
export declare interface ApiGetHuntFileArgs {
  readonly huntId?: string;
  readonly clientId?: string;
  readonly timestamp?: RDFDatetime;
  readonly vfsPath?: string;
}

/** ApiGetHuntFilesArchiveArgs proto mapping. */
export declare interface ApiGetHuntFilesArchiveArgs {
  readonly huntId?: string;
  readonly archiveFormat?: ApiGetHuntFilesArchiveArgsArchiveFormat;
}

/** ApiGetHuntFilesArchiveArgs.ArchiveFormat proto mapping. */
export enum ApiGetHuntFilesArchiveArgsArchiveFormat {
  ZIP = 'ZIP',
  TAR_GZ = 'TAR_GZ',
}

/** ApiGetHuntResultsExportCommandArgs proto mapping. */
export declare interface ApiGetHuntResultsExportCommandArgs {
  readonly huntId?: string;
}

/** ApiGetHuntResultsExportCommandResult proto mapping. */
export declare interface ApiGetHuntResultsExportCommandResult {
  readonly command?: string;
}

/** ApiGetHuntStatsArgs proto mapping. */
export declare interface ApiGetHuntStatsArgs {
  readonly huntId?: string;
}

/** ApiGetHuntStatsResult proto mapping. */
export declare interface ApiGetHuntStatsResult {
  readonly stats?: ClientResourcesStats;
}

/** ApiGetLastClientIPAddressArgs proto mapping. */
export declare interface ApiGetLastClientIPAddressArgs {
  readonly clientId?: string;
}

/** ApiGetLastClientIPAddressResult proto mapping. */
export declare interface ApiGetLastClientIPAddressResult {
  readonly ip?: string;
  readonly info?: string;
  readonly status?: ApiGetLastClientIPAddressResultStatus;
}

/** ApiGetLastClientIPAddressResult.Status proto mapping. */
export enum ApiGetLastClientIPAddressResultStatus {
  UNKNOWN = 'UNKNOWN',
  INTERNAL = 'INTERNAL',
  EXTERNAL = 'EXTERNAL',
  VPN = 'VPN',
}

/** ApiGetOpenApiDescriptionResult proto mapping. */
export declare interface ApiGetOpenApiDescriptionResult {
  readonly openapiDescription?: string;
}

/** ApiGetOsqueryResultsArgs proto mapping. */
export declare interface ApiGetOsqueryResultsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly format?: ApiGetOsqueryResultsArgsFormat;
}

/** ApiGetOsqueryResultsArgs.Format proto mapping. */
export enum ApiGetOsqueryResultsArgsFormat {
  UNSPECIFIED = 'UNSPECIFIED',
  CSV = 'CSV',
}

/** ApiGetPendingUserNotificationsCountResult proto mapping. */
export declare interface ApiGetPendingUserNotificationsCountResult {
  readonly count?: ProtoInt64;
}

/** ApiGetVfsFileContentUpdateStateArgs proto mapping. */
export declare interface ApiGetVfsFileContentUpdateStateArgs {
  readonly clientId?: string;
  readonly operationId?: string;
}

/** ApiGetVfsFileContentUpdateStateResult proto mapping. */
export declare interface ApiGetVfsFileContentUpdateStateResult {
  readonly state?: ApiGetVfsFileContentUpdateStateResultState;
}

/** ApiGetVfsFileContentUpdateStateResult.State proto mapping. */
export enum ApiGetVfsFileContentUpdateStateResultState {
  RUNNING = 'RUNNING',
  FINISHED = 'FINISHED',
}

/** ApiGetVfsFilesArchiveArgs proto mapping. */
export declare interface ApiGetVfsFilesArchiveArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly timestamp?: RDFDatetime;
}

/** ApiGetVfsRefreshOperationStateArgs proto mapping. */
export declare interface ApiGetVfsRefreshOperationStateArgs {
  readonly clientId?: string;
  readonly operationId?: string;
}

/** ApiGetVfsRefreshOperationStateResult proto mapping. */
export declare interface ApiGetVfsRefreshOperationStateResult {
  readonly state?: ApiGetVfsRefreshOperationStateResultState;
}

/** ApiGetVfsRefreshOperationStateResult.State proto mapping. */
export enum ApiGetVfsRefreshOperationStateResultState {
  RUNNING = 'RUNNING',
  FINISHED = 'FINISHED',
}

/** ApiGetVfsTimelineArgs proto mapping. */
export declare interface ApiGetVfsTimelineArgs {
  readonly clientId?: string;
  readonly filePath?: string;
}

/** ApiGetVfsTimelineAsCsvArgs proto mapping. */
export declare interface ApiGetVfsTimelineAsCsvArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly format?: ApiGetVfsTimelineAsCsvArgsFormat;
}

/** ApiGetVfsTimelineAsCsvArgs.Format proto mapping. */
export enum ApiGetVfsTimelineAsCsvArgsFormat {
  UNSET = 'UNSET',
  GRR = 'GRR',
  BODY = 'BODY',
}

/** ApiGetVfsTimelineResult proto mapping. */
export declare interface ApiGetVfsTimelineResult {
  readonly items?: readonly ApiVfsTimelineItem[];
}

/** ApiGrantClientApprovalArgs proto mapping. */
export declare interface ApiGrantClientApprovalArgs {
  readonly clientId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiGrantCronJobApprovalArgs proto mapping. */
export declare interface ApiGrantCronJobApprovalArgs {
  readonly cronJobId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiGrantHuntApprovalArgs proto mapping. */
export declare interface ApiGrantHuntApprovalArgs {
  readonly huntId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiGrrBinary proto mapping. */
export declare interface ApiGrrBinary {
  readonly type?: ApiGrrBinaryType;
  readonly path?: string;
  readonly size?: ByteSize;
  readonly timestamp?: RDFDatetime;
  readonly hasValidSignature?: boolean;
}

/** ApiGrrBinary.Type proto mapping. */
export enum ApiGrrBinaryType {
  PYTHON_HACK = 'PYTHON_HACK',
  EXECUTABLE = 'EXECUTABLE',
  COMPONENT_DEPRECATED = 'COMPONENT_DEPRECATED',
}

/** ApiGrrUser proto mapping. */
export declare interface ApiGrrUser {
  readonly username?: string;
  readonly settings?: GUISettings;
  readonly userType?: ApiGrrUserUserType;
  readonly email?: string;
}

/** ApiGrrUser.UserType proto mapping. */
export enum ApiGrrUserUserType {
  USER_TYPE_NONE = 'USER_TYPE_NONE',
  USER_TYPE_STANDARD = 'USER_TYPE_STANDARD',
  USER_TYPE_ADMIN = 'USER_TYPE_ADMIN',
}

/** ApiHunt proto mapping. */
export declare interface ApiHunt {
  readonly urn?: SessionID;
  readonly huntId?: string;
  readonly huntType?: ApiHuntHuntType;
  readonly name?: string;
  readonly state?: ApiHuntState;
  readonly stateReason?: ApiHuntStateReason;
  readonly stateComment?: string;
  readonly flowName?: string;
  readonly flowArgs?: Any;
  readonly huntRunnerArgs?: HuntRunnerArgs;
  readonly allClientsCount?: ProtoInt64;
  readonly remainingClientsCount?: ProtoInt64;
  readonly completedClientsCount?: ProtoInt64;
  readonly failedClientsCount?: ProtoInt64;
  readonly crashedClientsCount?: ProtoInt64;
  readonly crashLimit?: ProtoInt64;
  readonly clientLimit?: ProtoInt64;
  readonly clientRate?: ProtoFloat;
  readonly created?: RDFDatetime;
  readonly initStartTime?: RDFDatetime;
  readonly lastStartTime?: RDFDatetime;
  readonly deprecatedExpires?: RDFDatetime;
  readonly duration?: DurationSeconds;
  readonly creator?: string;
  readonly description?: string;
  readonly clientRuleSet?: ForemanClientRuleSet;
  readonly isRobot?: boolean;
  readonly totalCpuUsage?: ProtoFloat;
  readonly totalNetUsage?: ProtoInt64;
  readonly clientsWithResultsCount?: ProtoInt64;
  readonly resultsCount?: ProtoInt64;
  readonly originalObject?: ApiFlowLikeObjectReference;
  readonly internalError?: string;
}

/** ApiHunt.HuntType proto mapping. */
export enum ApiHuntHuntType {
  UNSET = 'UNSET',
  STANDARD = 'STANDARD',
  VARIABLE = 'VARIABLE',
}

/** ApiHunt.State proto mapping. */
export enum ApiHuntState {
  PAUSED = 'PAUSED',
  STARTED = 'STARTED',
  STOPPED = 'STOPPED',
  COMPLETED = 'COMPLETED',
}

/** ApiHunt.StateReason proto mapping. */
export enum ApiHuntStateReason {
  UNKNOWN = 'UNKNOWN',
  DEADLINE_REACHED = 'DEADLINE_REACHED',
  TOTAL_CLIENTS_EXCEEDED = 'TOTAL_CLIENTS_EXCEEDED',
  TOTAL_CRASHES_EXCEEDED = 'TOTAL_CRASHES_EXCEEDED',
  TOTAL_NETWORK_EXCEEDED = 'TOTAL_NETWORK_EXCEEDED',
  AVG_RESULTS_EXCEEDED = 'AVG_RESULTS_EXCEEDED',
  AVG_NETWORK_EXCEEDED = 'AVG_NETWORK_EXCEEDED',
  AVG_CPU_EXCEEDED = 'AVG_CPU_EXCEEDED',
  TRIGGERED_BY_USER = 'TRIGGERED_BY_USER',
}

/** ApiHuntApproval proto mapping. */
export declare interface ApiHuntApproval {
  readonly subject?: ApiHunt;
  readonly id?: string;
  readonly requestor?: string;
  readonly reason?: string;
  readonly isValid?: boolean;
  readonly isValidMessage?: string;
  readonly emailMessageId?: string;
  readonly notifiedUsers?: readonly string[];
  readonly emailCcAddresses?: readonly string[];
  readonly approvers?: readonly string[];
  readonly copiedFromHunt?: ApiHunt;
  readonly copiedFromFlow?: ApiFlow;
  readonly expirationTimeUs?: RDFDatetime;
}

/** ApiHuntClient proto mapping. */
export declare interface ApiHuntClient {
  readonly clientId?: string;
  readonly flowId?: string;
}

/** ApiHuntError proto mapping. */
export declare interface ApiHuntError {
  readonly clientId?: string;
  readonly logMessage?: string;
  readonly backtrace?: string;
  readonly timestamp?: RDFDatetime;
}

/** ApiHuntLog proto mapping. */
export declare interface ApiHuntLog {
  readonly clientId?: string;
  readonly logMessage?: string;
  readonly flowName?: string;
  readonly flowId?: string;
  readonly timestamp?: RDFDatetime;
}

/** ApiHuntReference proto mapping. */
export declare interface ApiHuntReference {
  readonly huntId?: string;
}

/** ApiHuntResult proto mapping. */
export declare interface ApiHuntResult {
  readonly clientId?: string;
  readonly payload?: Any;
  readonly timestamp?: RDFDatetime;
}

/** ApiInterrogateClientArgs proto mapping. */
export declare interface ApiInterrogateClientArgs {
  readonly clientId?: string;
}

/** ApiInterrogateClientResult proto mapping. */
export declare interface ApiInterrogateClientResult {
  readonly operationId?: string;
}

/** ApiKillFleetspeakArgs proto mapping. */
export declare interface ApiKillFleetspeakArgs {
  readonly clientId?: string;
  readonly force?: boolean;
}

/** ApiListAllFlowOutputPluginLogsArgs proto mapping. */
export declare interface ApiListAllFlowOutputPluginLogsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListAllFlowOutputPluginLogsResult proto mapping. */
export declare interface ApiListAllFlowOutputPluginLogsResult {
  readonly items?: readonly FlowOutputPluginLogEntry[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListAndResetUserNotificationsArgs proto mapping. */
export declare interface ApiListAndResetUserNotificationsArgs {
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly filter?: string;
}

/** ApiListAndResetUserNotificationsResult proto mapping. */
export declare interface ApiListAndResetUserNotificationsResult {
  readonly items?: readonly ApiNotification[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListApiMethodsResult proto mapping. */
export declare interface ApiListApiMethodsResult {
  readonly items?: readonly ApiMethod[];
}

/** ApiListApproverSuggestionsArgs proto mapping. */
export declare interface ApiListApproverSuggestionsArgs {
  readonly usernameQuery?: string;
}

/** ApiListApproverSuggestionsResult proto mapping. */
export declare interface ApiListApproverSuggestionsResult {
  readonly suggestions?: readonly ApiListApproverSuggestionsResultApproverSuggestion[];
}

/** ApiListApproverSuggestionsResult.ApproverSuggestion proto mapping. */
export declare interface ApiListApproverSuggestionsResultApproverSuggestion {
  readonly username?: string;
}

/** ApiListArtifactsArgs proto mapping. */
export declare interface ApiListArtifactsArgs {
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListArtifactsResult proto mapping. */
export declare interface ApiListArtifactsResult {
  readonly items?: readonly ArtifactDescriptor[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListClientApprovalsArgs proto mapping. */
export declare interface ApiListClientApprovalsArgs {
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly clientId?: string;
  readonly state?: ApiListClientApprovalsArgsState;
}

/** ApiListClientApprovalsArgs.State proto mapping. */
export enum ApiListClientApprovalsArgsState {
  ANY = 'ANY',
  VALID = 'VALID',
  INVALID = 'INVALID',
}

/** ApiListClientApprovalsResult proto mapping. */
export declare interface ApiListClientApprovalsResult {
  readonly items?: readonly ApiClientApproval[];
}

/** ApiListClientCrashesArgs proto mapping. */
export declare interface ApiListClientCrashesArgs {
  readonly clientId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly filter?: string;
}

/** ApiListClientCrashesResult proto mapping. */
export declare interface ApiListClientCrashesResult {
  readonly items?: readonly ClientCrash[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListClientsLabelsResult proto mapping. */
export declare interface ApiListClientsLabelsResult {
  readonly items?: readonly ClientLabel[];
}

/** ApiListCronJobApprovalsArgs proto mapping. */
export declare interface ApiListCronJobApprovalsArgs {
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListCronJobApprovalsResult proto mapping. */
export declare interface ApiListCronJobApprovalsResult {
  readonly items?: readonly ApiCronJobApproval[];
}

/** ApiListCronJobRunsArgs proto mapping. */
export declare interface ApiListCronJobRunsArgs {
  readonly cronJobId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListCronJobRunsResult proto mapping. */
export declare interface ApiListCronJobRunsResult {
  readonly items?: readonly ApiCronJobRun[];
}

/** ApiListCronJobsArgs proto mapping. */
export declare interface ApiListCronJobsArgs {
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListCronJobsResult proto mapping. */
export declare interface ApiListCronJobsResult {
  readonly items?: readonly ApiCronJob[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListFilesArgs proto mapping. */
export declare interface ApiListFilesArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly filter?: string;
  readonly directoriesOnly?: boolean;
  readonly timestamp?: RDFDatetime;
}

/** ApiListFilesResult proto mapping. */
export declare interface ApiListFilesResult {
  readonly items?: readonly ApiFile[];
}

/** ApiListFlowDescriptorsResult proto mapping. */
export declare interface ApiListFlowDescriptorsResult {
  readonly items?: readonly ApiFlowDescriptor[];
}

/** ApiListFlowLogsArgs proto mapping. */
export declare interface ApiListFlowLogsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly filter?: string;
}

/** ApiListFlowLogsResult proto mapping. */
export declare interface ApiListFlowLogsResult {
  readonly items?: readonly ApiFlowLog[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListFlowOutputPluginErrorsArgs proto mapping. */
export declare interface ApiListFlowOutputPluginErrorsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly pluginId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListFlowOutputPluginErrorsResult proto mapping. */
export declare interface ApiListFlowOutputPluginErrorsResult {
  readonly items?: readonly OutputPluginBatchProcessingStatus[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListFlowOutputPluginLogsArgs proto mapping. */
export declare interface ApiListFlowOutputPluginLogsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly pluginId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListFlowOutputPluginLogsResult proto mapping. */
export declare interface ApiListFlowOutputPluginLogsResult {
  readonly items?: readonly OutputPluginBatchProcessingStatus[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListFlowOutputPluginsArgs proto mapping. */
export declare interface ApiListFlowOutputPluginsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
}

/** ApiListFlowOutputPluginsResult proto mapping. */
export declare interface ApiListFlowOutputPluginsResult {
  readonly items?: readonly ApiOutputPlugin[];
}

/** ApiListFlowRequestsArgs proto mapping. */
export declare interface ApiListFlowRequestsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListFlowRequestsResult proto mapping. */
export declare interface ApiListFlowRequestsResult {
  readonly items?: readonly ApiFlowRequest[];
}

/** ApiListFlowResultsArgs proto mapping. */
export declare interface ApiListFlowResultsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly filter?: string;
  readonly withTag?: string;
  readonly withType?: string;
}

/** ApiListFlowResultsResult proto mapping. */
export declare interface ApiListFlowResultsResult {
  readonly items?: readonly ApiFlowResult[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListFlowsArgs proto mapping. */
export declare interface ApiListFlowsArgs {
  readonly clientId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly topFlowsOnly?: boolean;
  readonly minStartedAt?: RDFDatetime;
  readonly maxStartedAt?: RDFDatetime;
  readonly humanFlowsOnly?: boolean;
}

/** ApiListFlowsResult proto mapping. */
export declare interface ApiListFlowsResult {
  readonly items?: readonly ApiFlow[];
}

/** ApiListGrrBinariesArgs proto mapping. */
export declare interface ApiListGrrBinariesArgs {
  readonly includeMetadata?: boolean;
}

/** ApiListGrrBinariesResult proto mapping. */
export declare interface ApiListGrrBinariesResult {
  readonly items?: readonly ApiGrrBinary[];
}

/** ApiListHuntApprovalsArgs proto mapping. */
export declare interface ApiListHuntApprovalsArgs {
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly huntId?: string;
}

/** ApiListHuntApprovalsResult proto mapping. */
export declare interface ApiListHuntApprovalsResult {
  readonly items?: readonly ApiHuntApproval[];
}

/** ApiListHuntClientsArgs proto mapping. */
export declare interface ApiListHuntClientsArgs {
  readonly huntId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly clientStatus?: ApiListHuntClientsArgsClientStatus;
}

/** ApiListHuntClientsArgs.ClientStatus proto mapping. */
export enum ApiListHuntClientsArgsClientStatus {
  STARTED = 'STARTED',
  OUTSTANDING = 'OUTSTANDING',
  COMPLETED = 'COMPLETED',
}

/** ApiListHuntClientsResult proto mapping. */
export declare interface ApiListHuntClientsResult {
  readonly items?: readonly ApiHuntClient[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListHuntCrashesArgs proto mapping. */
export declare interface ApiListHuntCrashesArgs {
  readonly huntId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListHuntCrashesResult proto mapping. */
export declare interface ApiListHuntCrashesResult {
  readonly items?: readonly ClientCrash[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListHuntErrorsArgs proto mapping. */
export declare interface ApiListHuntErrorsArgs {
  readonly huntId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly filter?: string;
}

/** ApiListHuntErrorsResult proto mapping. */
export declare interface ApiListHuntErrorsResult {
  readonly items?: readonly ApiHuntError[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListHuntLogsArgs proto mapping. */
export declare interface ApiListHuntLogsArgs {
  readonly huntId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly filter?: string;
}

/** ApiListHuntLogsResult proto mapping. */
export declare interface ApiListHuntLogsResult {
  readonly items?: readonly ApiHuntLog[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListHuntOutputPluginErrorsArgs proto mapping. */
export declare interface ApiListHuntOutputPluginErrorsArgs {
  readonly huntId?: string;
  readonly pluginId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListHuntOutputPluginErrorsResult proto mapping. */
export declare interface ApiListHuntOutputPluginErrorsResult {
  readonly items?: readonly OutputPluginBatchProcessingStatus[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListHuntOutputPluginLogsArgs proto mapping. */
export declare interface ApiListHuntOutputPluginLogsArgs {
  readonly huntId?: string;
  readonly pluginId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiListHuntOutputPluginLogsResult proto mapping. */
export declare interface ApiListHuntOutputPluginLogsResult {
  readonly items?: readonly OutputPluginBatchProcessingStatus[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListHuntOutputPluginsArgs proto mapping. */
export declare interface ApiListHuntOutputPluginsArgs {
  readonly huntId?: string;
}

/** ApiListHuntOutputPluginsResult proto mapping. */
export declare interface ApiListHuntOutputPluginsResult {
  readonly items?: readonly ApiOutputPlugin[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListHuntResultsArgs proto mapping. */
export declare interface ApiListHuntResultsArgs {
  readonly huntId?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly filter?: string;
  readonly withType?: string;
}

/** ApiListHuntResultsResult proto mapping. */
export declare interface ApiListHuntResultsResult {
  readonly items?: readonly ApiHuntResult[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListHuntsArgs proto mapping. */
export declare interface ApiListHuntsArgs {
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
  readonly createdBy?: string;
  readonly descriptionContains?: string;
  readonly activeWithin?: DurationSeconds;
  readonly withFullSummary?: boolean;
  readonly robotFilter?: ApiListHuntsArgsRobotFilter;
  readonly withState?: ApiHuntState;
}

/** ApiListHuntsArgs.RobotFilter proto mapping. */
export enum ApiListHuntsArgsRobotFilter {
  UNKNOWN = 'UNKNOWN',
  NO_ROBOTS = 'NO_ROBOTS',
  ONLY_ROBOTS = 'ONLY_ROBOTS',
}

/** ApiListHuntsResult proto mapping. */
export declare interface ApiListHuntsResult {
  readonly items?: readonly ApiHunt[];
  readonly totalCount?: ProtoInt64;
}

/** ApiListKbFieldsResult proto mapping. */
export declare interface ApiListKbFieldsResult {
  readonly items?: readonly string[];
}

/** ApiListOutputPluginDescriptorsResult proto mapping. */
export declare interface ApiListOutputPluginDescriptorsResult {
  readonly items?: readonly ApiOutputPluginDescriptor[];
}

/** ApiListPendingUserNotificationsArgs proto mapping. */
export declare interface ApiListPendingUserNotificationsArgs {
  readonly timestamp?: RDFDatetime;
}

/** ApiListPendingUserNotificationsResult proto mapping. */
export declare interface ApiListPendingUserNotificationsResult {
  readonly items?: readonly ApiNotification[];
}

/** ApiListScheduledFlowsArgs proto mapping. */
export declare interface ApiListScheduledFlowsArgs {
  readonly clientId?: string;
  readonly creator?: string;
}

/** ApiListScheduledFlowsResult proto mapping. */
export declare interface ApiListScheduledFlowsResult {
  readonly scheduledFlows?: readonly ApiScheduledFlow[];
}

/** ApiListSignedCommandsResult proto mapping. */
export declare interface ApiListSignedCommandsResult {
  readonly signedCommands?: readonly ApiSignedCommand[];
}

/** ApiMethod proto mapping. */
export declare interface ApiMethod {
  readonly name?: string;
  readonly category?: string;
  readonly doc?: string;
  readonly httpRoute?: string;
  readonly httpMethods?: readonly string[];
  readonly argsTypeUrl?: string;
  readonly resultTypeUrl?: string;
}

/** ApiModifyCronJobArgs proto mapping. */
export declare interface ApiModifyCronJobArgs {
  readonly cronJobId?: string;
  readonly enabled?: boolean;
}

/** ApiModifyHuntArgs proto mapping. */
export declare interface ApiModifyHuntArgs {
  readonly huntId?: string;
  readonly state?: ApiHuntState;
  readonly clientLimit?: ProtoInt64;
  readonly clientRate?: ProtoInt64;
  readonly deprecatedExpires?: RDFDatetime;
  readonly duration?: DurationSeconds;
}

/** ApiNotification proto mapping. */
export declare interface ApiNotification {
  readonly timestamp?: RDFDatetime;
  readonly notificationType?: UserNotificationType;
  readonly message?: string;
  readonly reference?: ApiNotificationReference;
  readonly isPending?: boolean;
}

/** ApiNotificationClientApprovalReference proto mapping. */
export declare interface ApiNotificationClientApprovalReference {
  readonly clientId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiNotificationClientReference proto mapping. */
export declare interface ApiNotificationClientReference {
  readonly clientId?: string;
}

/** ApiNotificationCronJobApprovalReference proto mapping. */
export declare interface ApiNotificationCronJobApprovalReference {
  readonly cronJobId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiNotificationCronReference proto mapping. */
export declare interface ApiNotificationCronReference {
  readonly cronJobId?: string;
}

/** ApiNotificationFlowReference proto mapping. */
export declare interface ApiNotificationFlowReference {
  readonly clientId?: string;
  readonly flowId?: string;
}

/** ApiNotificationHuntApprovalReference proto mapping. */
export declare interface ApiNotificationHuntApprovalReference {
  readonly huntId?: string;
  readonly approvalId?: string;
  readonly username?: string;
}

/** ApiNotificationHuntReference proto mapping. */
export declare interface ApiNotificationHuntReference {
  readonly huntId?: string;
}

/** ApiNotificationReference proto mapping. */
export declare interface ApiNotificationReference {
  readonly type?: ApiNotificationReferenceType;
  readonly client?: ApiNotificationClientReference;
  readonly hunt?: ApiNotificationHuntReference;
  readonly cron?: ApiNotificationCronReference;
  readonly flow?: ApiNotificationFlowReference;
  readonly vfs?: ApiNotificationVfsReference;
  readonly clientApproval?: ApiNotificationClientApprovalReference;
  readonly huntApproval?: ApiNotificationHuntApprovalReference;
  readonly cronJobApproval?: ApiNotificationCronJobApprovalReference;
  readonly unknown?: ApiNotificationUnknownReference;
}

/** ApiNotificationReference.Type proto mapping. */
export enum ApiNotificationReferenceType {
  UNSET = 'UNSET',
  CLIENT = 'CLIENT',
  HUNT = 'HUNT',
  CRON = 'CRON',
  FLOW = 'FLOW',
  VFS = 'VFS',
  CLIENT_APPROVAL = 'CLIENT_APPROVAL',
  HUNT_APPROVAL = 'HUNT_APPROVAL',
  CRON_JOB_APPROVAL = 'CRON_JOB_APPROVAL',
  UNKNOWN = 'UNKNOWN',
}

/** ApiNotificationUnknownReference proto mapping. */
export declare interface ApiNotificationUnknownReference {
  readonly sourceUrn?: RDFURN;
  readonly subjectUrn?: RDFURN;
}

/** ApiNotificationVfsReference proto mapping. */
export declare interface ApiNotificationVfsReference {
  readonly vfsPath?: string;
  readonly clientId?: string;
}

/** ApiOutputPlugin proto mapping. */
export declare interface ApiOutputPlugin {
  readonly id?: string;
  readonly pluginDescriptor?: OutputPluginDescriptor;
  readonly state?: Any;
}

/** ApiOutputPluginDescriptor proto mapping. */
export declare interface ApiOutputPluginDescriptor {
  readonly pluginType?: ApiOutputPluginDescriptorPluginType;
  readonly name?: string;
  readonly friendlyName?: string;
  readonly description?: string;
  readonly argsType?: string;
}

/** ApiOutputPluginDescriptor.PluginType proto mapping. */
export enum ApiOutputPluginDescriptorPluginType {
  LEGACY = 'LEGACY',
  INSTANT = 'INSTANT',
  LIVE = 'LIVE',
}

/** ApiRemoveClientsLabelsArgs proto mapping. */
export declare interface ApiRemoveClientsLabelsArgs {
  readonly clientIds?: readonly string[];
  readonly labels?: readonly string[];
}

/** ApiRestartFleetspeakGrrServiceArgs proto mapping. */
export declare interface ApiRestartFleetspeakGrrServiceArgs {
  readonly clientId?: string;
}

/** ApiScheduledFlow proto mapping. */
export declare interface ApiScheduledFlow {
  readonly scheduledFlowId?: string;
  readonly clientId?: string;
  readonly creator?: string;
  readonly flowName?: string;
  readonly flowArgs?: Any;
  readonly runnerArgs?: FlowRunnerArgs;
  readonly createTime?: RDFDatetime;
  readonly error?: string;
}

/** ApiSearchClientsArgs proto mapping. */
export declare interface ApiSearchClientsArgs {
  readonly query?: string;
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
}

/** ApiSearchClientsResult proto mapping. */
export declare interface ApiSearchClientsResult {
  readonly items?: readonly ApiClient[];
}

/** ApiSignedCommand proto mapping. */
export declare interface ApiSignedCommand {
  readonly id?: string;
  readonly operatingSystem?: ApiSignedCommandOS;
  readonly command?: ProtoBytes;
  readonly ed25519Signature?: ProtoBytes;
  readonly sourcePath?: string;
}

/** ApiSignedCommand.OS proto mapping. */
export enum ApiSignedCommandOS {
  UNSET = 'UNSET',
  LINUX = 'LINUX',
  MACOS = 'MACOS',
  WINDOWS = 'WINDOWS',
}

/** ApiTimelineBodyOpts proto mapping. */
export declare interface ApiTimelineBodyOpts {
  readonly timestampSubsecondPrecision?: boolean;
  readonly inodeNtfsFileReferenceFormat?: boolean;
  readonly backslashEscape?: boolean;
  readonly carriageReturnEscape?: boolean;
  readonly nonPrintableEscape?: boolean;
}

/** ApiTypeCount proto mapping. */
export declare interface ApiTypeCount {
  readonly type?: string;
  readonly count?: ProtoInt64;
}

/** ApiUiConfig proto mapping. */
export declare interface ApiUiConfig {
  readonly heading?: string;
  readonly reportUrl?: string;
  readonly helpUrl?: string;
  readonly grrVersion?: string;
  readonly profileImageUrl?: string;
  readonly defaultHuntRunnerArgs?: HuntRunnerArgs;
  readonly huntConfig?: AdminUIHuntConfig;
  readonly defaultOutputPlugins?: readonly OutputPluginDescriptor[];
  readonly clientWarnings?: AdminUIClientWarningsConfigOption;
  readonly defaultAccessDurationSeconds?: ProtoUint64;
  readonly maxAccessDurationSeconds?: ProtoUint64;
}

/** ApiUnscheduleFlowArgs proto mapping. */
export declare interface ApiUnscheduleFlowArgs {
  readonly clientId?: string;
  readonly scheduledFlowId?: string;
}

/** ApiUnscheduleFlowResult proto mapping. */
export declare interface ApiUnscheduleFlowResult {
}

/** ApiUpdateVfsFileContentArgs proto mapping. */
export declare interface ApiUpdateVfsFileContentArgs {
  readonly clientId?: string;
  readonly filePath?: string;
}

/** ApiUpdateVfsFileContentResult proto mapping. */
export declare interface ApiUpdateVfsFileContentResult {
  readonly operationId?: string;
}

/** ApiUploadArtifactArgs proto mapping. */
export declare interface ApiUploadArtifactArgs {
  readonly artifact?: string;
}

/** ApiUploadYaraSignatureArgs proto mapping. */
export declare interface ApiUploadYaraSignatureArgs {
  readonly signature?: string;
}

/** ApiUploadYaraSignatureResult proto mapping. */
export declare interface ApiUploadYaraSignatureResult {
  readonly blobId?: ProtoBytes;
}

/** ApiVerifyAccessArgs proto mapping. */
export declare interface ApiVerifyAccessArgs {
  readonly clientId?: string;
}

/** ApiVerifyAccessResult proto mapping. */
export declare interface ApiVerifyAccessResult {
}

/** ApiVerifyHuntAccessArgs proto mapping. */
export declare interface ApiVerifyHuntAccessArgs {
  readonly huntId?: string;
}

/** ApiVerifyHuntAccessResult proto mapping. */
export declare interface ApiVerifyHuntAccessResult {
}

/** ApiVfsTimelineItem proto mapping. */
export declare interface ApiVfsTimelineItem {
  readonly timestamp?: RDFDatetime;
  readonly filePath?: string;
  readonly action?: ApiVfsTimelineItemFileActionType;
}

/** ApiVfsTimelineItem.FileActionType proto mapping. */
export enum ApiVfsTimelineItemFileActionType {
  MODIFICATION = 'MODIFICATION',
  ACCESS = 'ACCESS',
  METADATA_CHANGED = 'METADATA_CHANGED',
}

/** Artifact proto mapping. */
export declare interface Artifact {
  readonly name?: string;
  readonly conditions?: readonly string[];
  readonly doc?: string;
  readonly supportedOs?: readonly string[];
  readonly urls?: readonly string[];
  readonly sources?: readonly ArtifactSource[];
  readonly errorMessage?: string;
  readonly aliases?: readonly string[];
}

/** ArtifactCollectorFlowArgs proto mapping. */
export declare interface ArtifactCollectorFlowArgs {
  readonly artifactList?: readonly string[];
  readonly useRawFilesystemAccess?: boolean;
  readonly splitOutputByArtifact?: boolean;
  readonly knowledgeBase?: KnowledgeBase;
  readonly errorOnNoResults?: boolean;
  readonly maxFileSize?: ByteSize;
  readonly ignoreInterpolationErrors?: boolean;
  readonly recollectKnowledgeBase?: boolean;
  readonly implementationType?: PathSpecImplementationType;
}

/** ArtifactCollectorFlowProgress proto mapping. */
export declare interface ArtifactCollectorFlowProgress {
  readonly artifacts?: readonly ArtifactProgress[];
}

/** ArtifactCollectorFlowStore proto mapping. */
export declare interface ArtifactCollectorFlowStore {
  readonly knowledgeBase?: KnowledgeBase;
  readonly blobWaitCount?: ProtoInt32;
  readonly pathInfos?: readonly PathInfo[];
}

/** ArtifactDescriptor proto mapping. */
export declare interface ArtifactDescriptor {
  readonly artifact?: Artifact;
  readonly dependencies?: readonly string[];
  readonly pathDependencies?: readonly string[];
  readonly isCustom?: boolean;
  readonly errorMessage?: string;
}

/** ArtifactProgress proto mapping. */
export declare interface ArtifactProgress {
  readonly name?: string;
  readonly numResults?: ProtoUint32;
  readonly status?: ArtifactProgressStatus;
}

/** ArtifactProgress.Status proto mapping. */
export enum ArtifactProgressStatus {
  UNDEFINED = 'UNDEFINED',
  SUCCESS = 'SUCCESS',
  FAILURE = 'FAILURE',
  SKIPPED_DUE_TO_OS_CONDITION = 'SKIPPED_DUE_TO_OS_CONDITION',
}

/** ArtifactSource proto mapping. */
export declare interface ArtifactSource {
  readonly type?: ArtifactSourceSourceType;
  readonly attributes?: Dict;
  readonly conditions?: readonly string[];
  readonly supportedOs?: readonly string[];
}

/** ArtifactSource.SourceType proto mapping. */
export enum ArtifactSourceSourceType {
  COLLECTOR_TYPE_UNKNOWN = 'COLLECTOR_TYPE_UNKNOWN',
  FILE = 'FILE',
  REGISTRY_KEY = 'REGISTRY_KEY',
  REGISTRY_VALUE = 'REGISTRY_VALUE',
  WMI = 'WMI',
  PATH = 'PATH',
  ARTIFACT_GROUP = 'ARTIFACT_GROUP',
  COMMAND = 'COMMAND',
}

/** AttributedDict proto mapping. */
export declare interface AttributedDict {
  readonly dat?: readonly KeyValue[];
}

/** AuthenticodeSignedData proto mapping. */
export declare interface AuthenticodeSignedData {
  readonly revision?: ProtoUint64;
  readonly certType?: ProtoUint64;
  readonly certificate?: ProtoBytes;
}

/** BlobArray proto mapping. */
export declare interface BlobArray {
  readonly content?: readonly DataBlob[];
}

/** BlobImageChunkDescriptor proto mapping. */
export declare interface BlobImageChunkDescriptor {
  readonly offset?: ProtoUint64;
  readonly length?: ProtoUint64;
  readonly digest?: ProtoBytes;
}

/** BlobImageDescriptor proto mapping. */
export declare interface BlobImageDescriptor {
  readonly chunks?: readonly BlobImageChunkDescriptor[];
  readonly chunkSize?: ProtoUint64;
}

/** Browser proto mapping. */
export enum Browser {
  UNDEFINED = 'UNDEFINED',
  CHROMIUM_BASED_BROWSERS = 'CHROMIUM_BASED_BROWSERS',
  FIREFOX = 'FIREFOX',
  INTERNET_EXPLORER = 'INTERNET_EXPLORER',
  OPERA = 'OPERA',
  SAFARI = 'SAFARI',
}

/** BrowserProgress proto mapping. */
export declare interface BrowserProgress {
  readonly browser?: Browser;
  readonly status?: BrowserProgressStatus;
  readonly description?: string;
  readonly numCollectedFiles?: ProtoUint32;
  readonly flowId?: string;
}

/** BrowserProgress.Status proto mapping. */
export enum BrowserProgressStatus {
  UNDEFINED = 'UNDEFINED',
  IN_PROGRESS = 'IN_PROGRESS',
  SUCCESS = 'SUCCESS',
  ERROR = 'ERROR',
}

/** BufferReference proto mapping. */
export declare interface BufferReference {
  readonly offset?: ProtoUint64;
  readonly length?: ProtoUint64;
  readonly callback?: string;
  readonly data?: ProtoBytes;
  readonly pathspec?: PathSpec;
}

/** BytesValue proto mapping. */
export declare interface BytesValue {
  readonly value?: ProtoBytes;
}

/** ClientCrash proto mapping. */
export declare interface ClientCrash {
  readonly clientId?: string;
  readonly sessionId?: SessionID;
  readonly clientInfo?: ClientInformation;
  readonly timestamp?: RDFDatetime;
  readonly crashType?: string;
  readonly crashMessage?: string;
  readonly backtrace?: string;
}

/** ClientInformation proto mapping. */
export declare interface ClientInformation {
  readonly clientName?: string;
  readonly clientVersion?: ProtoUint32;
  readonly revision?: ProtoUint64;
  readonly buildTime?: string;
  readonly clientBinaryName?: string;
  readonly clientDescription?: string;
  readonly labels?: readonly string[];
  readonly timelineBtimeSupport?: boolean;
  readonly sandboxSupport?: boolean;
}

/** ClientLabel proto mapping. */
export declare interface ClientLabel {
  readonly name?: string;
  readonly owner?: string;
}

/** ClientResources proto mapping. */
export declare interface ClientResources {
  readonly clientId?: string;
  readonly sessionId?: SessionID;
  readonly cpuUsage?: CpuSeconds;
  readonly networkBytesSent?: ProtoUint64;
}

/** ClientResourcesStats proto mapping. */
export declare interface ClientResourcesStats {
  readonly userCpuStats?: RunningStats;
  readonly systemCpuStats?: RunningStats;
  readonly networkBytesSentStats?: RunningStats;
  readonly worstPerformers?: readonly ClientResources[];
}

/** ClientSnapshot proto mapping. */
export declare interface ClientSnapshot {
  readonly clientId?: string;
  readonly filesystems?: readonly Filesystem[];
  readonly osRelease?: string;
  readonly osVersion?: string;
  readonly arch?: string;
  readonly installTime?: RDFDatetime;
  readonly knowledgeBase?: KnowledgeBase;
  readonly grrConfiguration?: readonly StringMapEntry[];
  readonly libraryVersions?: readonly StringMapEntry[];
  readonly kernel?: string;
  readonly volumes?: readonly Volume[];
  readonly interfaces?: readonly Interface[];
  readonly hardwareInfo?: HardwareInfo;
  readonly memorySize?: ByteSize;
  readonly cloudInstance?: CloudInstance;
  readonly startupInfo?: StartupInfo;
  readonly edrAgents?: readonly EdrAgent[];
  readonly fleetspeakValidationInfo?: FleetspeakValidationInfo;
  readonly metadata?: ClientSnapshotMetadata;
  readonly timestamp?: RDFDatetime;
}

/** ClientSnapshotMetadata proto mapping. */
export declare interface ClientSnapshotMetadata {
  readonly sourceFlowId?: string;
}

/** CloudInstance proto mapping. */
export declare interface CloudInstance {
  readonly cloudType?: CloudInstanceInstanceType;
  readonly google?: GoogleCloudInstance;
  readonly amazon?: AmazonCloudInstance;
}

/** CloudInstance.InstanceType proto mapping. */
export enum CloudInstanceInstanceType {
  UNSET = 'UNSET',
  AMAZON = 'AMAZON',
  GOOGLE = 'GOOGLE',
}

/** CollectBrowserHistoryArgs proto mapping. */
export declare interface CollectBrowserHistoryArgs {
  readonly browsers?: readonly Browser[];
}

/** CollectBrowserHistoryProgress proto mapping. */
export declare interface CollectBrowserHistoryProgress {
  readonly browsers?: readonly BrowserProgress[];
}

/** CollectBrowserHistoryResult proto mapping. */
export declare interface CollectBrowserHistoryResult {
  readonly browser?: Browser;
  readonly statEntry?: StatEntry;
}

/** CollectCloudVMMetadataResult proto mapping. */
export declare interface CollectCloudVMMetadataResult {
  readonly vmMetadata?: CloudInstance;
}

/** CollectCloudVMMetadataStore proto mapping. */
export declare interface CollectCloudVMMetadataStore {
  readonly vmMetadata?: CloudInstance;
}

/** CollectDistroInfoResult proto mapping. */
export declare interface CollectDistroInfoResult {
  readonly name?: string;
  readonly release?: string;
  readonly versionMajor?: ProtoUint32;
  readonly versionMinor?: ProtoUint32;
}

/** CollectDistroInfoStore proto mapping. */
export declare interface CollectDistroInfoStore {
  readonly result?: CollectDistroInfoResult;
}

/** CollectFilesByKnownPathArgs proto mapping. */
export declare interface CollectFilesByKnownPathArgs {
  readonly paths?: readonly string[];
  readonly collectionLevel?: CollectFilesByKnownPathArgsCollectionLevel;
}

/** CollectFilesByKnownPathArgs.CollectionLevel proto mapping. */
export enum CollectFilesByKnownPathArgsCollectionLevel {
  UNDEFINED = 'UNDEFINED',
  STAT = 'STAT',
  HASH = 'HASH',
  CONTENT = 'CONTENT',
}

/** CollectFilesByKnownPathProgress proto mapping. */
export declare interface CollectFilesByKnownPathProgress {
  readonly numInProgress?: ProtoUint64;
  readonly numRawFsAccessRetries?: ProtoUint64;
  readonly numCollected?: ProtoUint64;
  readonly numFailed?: ProtoUint64;
}

/** CollectFilesByKnownPathResult proto mapping. */
export declare interface CollectFilesByKnownPathResult {
  readonly stat?: StatEntry;
  readonly hash?: Hash;
  readonly status?: CollectFilesByKnownPathResultStatus;
  readonly error?: string;
}

/** CollectFilesByKnownPathResult.Status proto mapping. */
export enum CollectFilesByKnownPathResultStatus {
  UNDEFINED = 'UNDEFINED',
  IN_PROGRESS = 'IN_PROGRESS',
  COLLECTED = 'COLLECTED',
  NOT_FOUND = 'NOT_FOUND',
  FAILED = 'FAILED',
}

/** CollectLargeFileFlowArgs proto mapping. */
export declare interface CollectLargeFileFlowArgs {
  readonly pathSpec?: PathSpec;
  readonly signedUrl?: string;
}

/** CollectLargeFileFlowProgress proto mapping. */
export declare interface CollectLargeFileFlowProgress {
  readonly sessionUri?: string;
}

/** CollectLargeFileFlowResult proto mapping. */
export declare interface CollectLargeFileFlowResult {
  readonly sessionUri?: string;
  readonly totalBytesSent?: ProtoUint64;
}

/** CollectLargeFileFlowStore proto mapping. */
export declare interface CollectLargeFileFlowStore {
  readonly encryptionKey?: ProtoBytes;
  readonly sessionUri?: string;
}

/** CollectMultipleFilesArgs proto mapping. */
export declare interface CollectMultipleFilesArgs {
  readonly pathExpressions?: readonly GlobExpression[];
  readonly modificationTime?: FileFinderModificationTimeCondition;
  readonly accessTime?: FileFinderAccessTimeCondition;
  readonly inodeChangeTime?: FileFinderInodeChangeTimeCondition;
  readonly size?: FileFinderSizeCondition;
  readonly extFlags?: FileFinderExtFlagsCondition;
  readonly contentsRegexMatch?: FileFinderContentsRegexMatchCondition;
  readonly contentsLiteralMatch?: FileFinderContentsLiteralMatchCondition;
}

/** CollectMultipleFilesProgress proto mapping. */
export declare interface CollectMultipleFilesProgress {
  readonly numFound?: ProtoUint64;
  readonly numInProgress?: ProtoUint64;
  readonly numRawFsAccessRetries?: ProtoUint64;
  readonly numCollected?: ProtoUint64;
  readonly numFailed?: ProtoUint64;
}

/** CollectMultipleFilesResult proto mapping. */
export declare interface CollectMultipleFilesResult {
  readonly stat?: StatEntry;
  readonly hash?: Hash;
  readonly status?: CollectMultipleFilesResultStatus;
  readonly error?: string;
}

/** CollectMultipleFilesResult.Status proto mapping. */
export enum CollectMultipleFilesResultStatus {
  UNDEFINED = 'UNDEFINED',
  COLLECTED = 'COLLECTED',
  FAILED = 'FAILED',
}

/** ContainerDetails proto mapping. */
export declare interface ContainerDetails {
  readonly containerId?: string;
  readonly imageName?: string;
  readonly command?: string;
  readonly createdAt?: ProtoUint64;
  readonly status?: string;
  readonly ports?: readonly string[];
  readonly names?: readonly string[];
  readonly labels?: readonly ContainerLabel[];
  readonly localVolumes?: string;
  readonly mounts?: readonly string[];
  readonly networks?: readonly string[];
  readonly runningSince?: string;
  readonly state?: ContainerDetailsContainerState;
  readonly containerCli?: ContainerDetailsContainerCli;
}

/** ContainerDetails.ContainerCli proto mapping. */
export enum ContainerDetailsContainerCli {
  UNSUPPORTED = 'UNSUPPORTED',
  CRICTL = 'CRICTL',
  DOCKER = 'DOCKER',
}

/** ContainerDetails.ContainerState proto mapping. */
export enum ContainerDetailsContainerState {
  CONTAINER_UNKNOWN = 'CONTAINER_UNKNOWN',
  CONTAINER_CREATED = 'CONTAINER_CREATED',
  CONTAINER_RUNNING = 'CONTAINER_RUNNING',
  CONTAINER_PAUSED = 'CONTAINER_PAUSED',
  CONTAINER_EXITED = 'CONTAINER_EXITED',
}

/** ContainerLabel proto mapping. */
export declare interface ContainerLabel {
  readonly label?: string;
  readonly value?: string;
}

/** CpuSeconds proto mapping. */
export declare interface CpuSeconds {
  readonly deprecatedUserCpuTime?: ProtoFloat;
  readonly deprecatedSystemCpuTime?: ProtoFloat;
  readonly userCpuTime?: ProtoDouble;
  readonly systemCpuTime?: ProtoDouble;
}

/** CronJobAction proto mapping. */
export declare interface CronJobAction {
  readonly actionType?: CronJobActionActionType;
  readonly systemCronAction?: SystemCronAction;
  readonly huntCronAction?: HuntCronAction;
}

/** CronJobAction.ActionType proto mapping. */
export enum CronJobActionActionType {
  UNSET = 'UNSET',
  SYSTEM_CRON_ACTION = 'SYSTEM_CRON_ACTION',
  HUNT_CRON_ACTION = 'HUNT_CRON_ACTION',
}

/** CronJobRun.CronJobRunStatus proto mapping. */
export enum CronJobRunCronJobRunStatus {
  UNSET = 'UNSET',
  RUNNING = 'RUNNING',
  FINISHED = 'FINISHED',
  ERROR = 'ERROR',
  LIFETIME_EXCEEDED = 'LIFETIME_EXCEEDED',
}

/** DataBlob proto mapping. */
export declare interface DataBlob {
  readonly integer?: ProtoInt64;
  readonly data?: ProtoBytes;
  readonly string?: string;
  readonly protoName?: string;
  readonly none?: string;
  readonly boolean?: boolean;
  readonly list?: BlobArray;
  readonly dict?: Dict;
  readonly rdfValue?: EmbeddedRDFValue;
  readonly float?: ProtoFloat;
  readonly set?: BlobArray;
  readonly compression?: DataBlobCompressionType;
}

/** DataBlob.CompressionType proto mapping. */
export enum DataBlobCompressionType {
  UNCOMPRESSED = 'UNCOMPRESSED',
  ZCOMPRESSION = 'ZCOMPRESSION',
}

/** DefaultFlowProgress proto mapping. */
export declare interface DefaultFlowProgress {
}

/** DefaultFlowStore proto mapping. */
export declare interface DefaultFlowStore {
}

/** DeleteGRRTempFilesArgs proto mapping. */
export declare interface DeleteGRRTempFilesArgs {
  readonly pathspec?: PathSpec;
}

/** Dict proto mapping. */
export declare interface Dict {
  readonly dat?: readonly KeyValue[];
}

/** DummyArgs proto mapping. */
export declare interface DummyArgs {
  readonly flowInput?: string;
}

/** DummyFlowResult proto mapping. */
export declare interface DummyFlowResult {
  readonly flowOutput?: string;
}

/** EdrAgent proto mapping. */
export declare interface EdrAgent {
  readonly name?: string;
  readonly agentId?: string;
  readonly backendId?: string;
}

/** EmailOutputPluginArgs proto mapping. */
export declare interface EmailOutputPluginArgs {
  readonly emailAddress?: string;
}

/** EmbeddedRDFValue proto mapping. */
export declare interface EmbeddedRDFValue {
  readonly name?: string;
  readonly data?: ProtoBytes;
}

/** EmptyFlowArgs proto mapping. */
export declare interface EmptyFlowArgs {
}

/** ExecuteBinaryResponse proto mapping. */
export declare interface ExecuteBinaryResponse {
  readonly exitStatus?: ProtoInt32;
  readonly stdout?: ProtoBytes;
  readonly stderr?: ProtoBytes;
  readonly timeUsed?: ProtoInt32;
}

/** ExecutePythonHackArgs proto mapping. */
export declare interface ExecutePythonHackArgs {
  readonly hackName?: string;
  readonly pyArgs?: Dict;
}

/** ExecutePythonHackResult proto mapping. */
export declare interface ExecutePythonHackResult {
  readonly resultString?: string;
}

/** ExecuteRequest proto mapping. */
export declare interface ExecuteRequest {
  readonly cmd?: string;
  readonly args?: readonly string[];
  readonly timeLimit?: ProtoInt32;
}

/** ExecuteResponse proto mapping. */
export declare interface ExecuteResponse {
  readonly request?: ExecuteRequest;
  readonly exitStatus?: ProtoInt32;
  readonly stdout?: ProtoBytes;
  readonly stderr?: ProtoBytes;
  readonly timeUsed?: ProtoInt32;
}

/** FileFinderAccessTimeCondition proto mapping. */
export declare interface FileFinderAccessTimeCondition {
  readonly minLastAccessTime?: RDFDatetime;
  readonly maxLastAccessTime?: RDFDatetime;
}

/** FileFinderAction proto mapping. */
export declare interface FileFinderAction {
  readonly actionType?: FileFinderActionAction;
  readonly hash?: FileFinderHashActionOptions;
  readonly download?: FileFinderDownloadActionOptions;
  readonly stat?: FileFinderStatActionOptions;
}

/** FileFinderAction.Action proto mapping. */
export enum FileFinderActionAction {
  STAT = 'STAT',
  HASH = 'HASH',
  DOWNLOAD = 'DOWNLOAD',
}

/** FileFinderArgs proto mapping. */
export declare interface FileFinderArgs {
  readonly paths?: readonly GlobExpression[];
  readonly pathtype?: PathSpecPathType;
  readonly conditions?: readonly FileFinderCondition[];
  readonly action?: FileFinderAction;
  readonly processNonRegularFiles?: boolean;
  readonly followLinks?: boolean;
  readonly xdev?: FileFinderArgsXDev;
  readonly implementationType?: PathSpecImplementationType;
}

/** FileFinderArgs.XDev proto mapping. */
export enum FileFinderArgsXDev {
  NEVER = 'NEVER',
  ALWAYS = 'ALWAYS',
  LOCAL = 'LOCAL',
}

/** FileFinderCondition proto mapping. */
export declare interface FileFinderCondition {
  readonly conditionType?: FileFinderConditionType;
  readonly modificationTime?: FileFinderModificationTimeCondition;
  readonly accessTime?: FileFinderAccessTimeCondition;
  readonly inodeChangeTime?: FileFinderInodeChangeTimeCondition;
  readonly size?: FileFinderSizeCondition;
  readonly extFlags?: FileFinderExtFlagsCondition;
  readonly contentsRegexMatch?: FileFinderContentsRegexMatchCondition;
  readonly contentsLiteralMatch?: FileFinderContentsLiteralMatchCondition;
}

/** FileFinderCondition.Type proto mapping. */
export enum FileFinderConditionType {
  MODIFICATION_TIME = 'MODIFICATION_TIME',
  ACCESS_TIME = 'ACCESS_TIME',
  INODE_CHANGE_TIME = 'INODE_CHANGE_TIME',
  SIZE = 'SIZE',
  EXT_FLAGS = 'EXT_FLAGS',
  CONTENTS_REGEX_MATCH = 'CONTENTS_REGEX_MATCH',
  CONTENTS_LITERAL_MATCH = 'CONTENTS_LITERAL_MATCH',
}

/** FileFinderContentsLiteralMatchCondition proto mapping. */
export declare interface FileFinderContentsLiteralMatchCondition {
  readonly literal?: RDFBytes;
  readonly mode?: FileFinderContentsLiteralMatchConditionMode;
  readonly startOffset?: ProtoUint64;
  readonly length?: ProtoUint64;
  readonly bytesBefore?: ProtoUint32;
  readonly bytesAfter?: ProtoUint32;
  readonly xorInKey?: ProtoUint32;
  readonly xorOutKey?: ProtoUint32;
}

/** FileFinderContentsLiteralMatchCondition.Mode proto mapping. */
export enum FileFinderContentsLiteralMatchConditionMode {
  ALL_HITS = 'ALL_HITS',
  FIRST_HIT = 'FIRST_HIT',
}

/** FileFinderContentsRegexMatchCondition proto mapping. */
export declare interface FileFinderContentsRegexMatchCondition {
  readonly regex?: RDFBytes;
  readonly mode?: FileFinderContentsRegexMatchConditionMode;
  readonly bytesBefore?: ProtoUint32;
  readonly bytesAfter?: ProtoUint32;
  readonly startOffset?: ProtoUint64;
  readonly length?: ProtoUint64;
}

/** FileFinderContentsRegexMatchCondition.Mode proto mapping. */
export enum FileFinderContentsRegexMatchConditionMode {
  ALL_HITS = 'ALL_HITS',
  FIRST_HIT = 'FIRST_HIT',
}

/** FileFinderDownloadActionOptions proto mapping. */
export declare interface FileFinderDownloadActionOptions {
  readonly maxSize?: ByteSize;
  readonly oversizedFilePolicy?: FileFinderDownloadActionOptionsOversizedFilePolicy;
  readonly useExternalStores?: boolean;
  readonly collectExtAttrs?: boolean;
  readonly chunkSize?: ProtoUint64;
}

/** FileFinderDownloadActionOptions.OversizedFilePolicy proto mapping. */
export enum FileFinderDownloadActionOptionsOversizedFilePolicy {
  SKIP = 'SKIP',
  HASH_TRUNCATED = 'HASH_TRUNCATED',
  DOWNLOAD_TRUNCATED = 'DOWNLOAD_TRUNCATED',
}

/** FileFinderExtFlagsCondition proto mapping. */
export declare interface FileFinderExtFlagsCondition {
  readonly linuxBitsSet?: ProtoUint32;
  readonly linuxBitsUnset?: ProtoUint32;
  readonly osxBitsSet?: ProtoUint32;
  readonly osxBitsUnset?: ProtoUint32;
}

/** FileFinderHashActionOptions proto mapping. */
export declare interface FileFinderHashActionOptions {
  readonly maxSize?: ByteSize;
  readonly oversizedFilePolicy?: FileFinderHashActionOptionsOversizedFilePolicy;
  readonly collectExtAttrs?: boolean;
}

/** FileFinderHashActionOptions.OversizedFilePolicy proto mapping. */
export enum FileFinderHashActionOptionsOversizedFilePolicy {
  SKIP = 'SKIP',
  HASH_TRUNCATED = 'HASH_TRUNCATED',
}

/** FileFinderInodeChangeTimeCondition proto mapping. */
export declare interface FileFinderInodeChangeTimeCondition {
  readonly minLastInodeChangeTime?: RDFDatetime;
  readonly maxLastInodeChangeTime?: RDFDatetime;
}

/** FileFinderModificationTimeCondition proto mapping. */
export declare interface FileFinderModificationTimeCondition {
  readonly minLastModifiedTime?: RDFDatetime;
  readonly maxLastModifiedTime?: RDFDatetime;
}

/** FileFinderProgress proto mapping. */
export declare interface FileFinderProgress {
  readonly filesFound?: ProtoUint64;
}

/** FileFinderResult proto mapping. */
export declare interface FileFinderResult {
  readonly statEntry?: StatEntry;
  readonly matches?: readonly BufferReference[];
  readonly hashEntry?: Hash;
  readonly transferredFile?: BlobImageDescriptor;
}

/** FileFinderSizeCondition proto mapping. */
export declare interface FileFinderSizeCondition {
  readonly minFileSize?: ProtoUint64;
  readonly maxFileSize?: ProtoUint64;
}

/** FileFinderStatActionOptions proto mapping. */
export declare interface FileFinderStatActionOptions {
  readonly resolveLinks?: boolean;
  readonly collectExtAttrs?: boolean;
}

/** FileFinderStore proto mapping. */
export declare interface FileFinderStore {
  readonly numBlobWaits?: ProtoUint64;
  readonly resultsPendingContent?: readonly FileFinderResult[];
}

/** Filesystem proto mapping. */
export declare interface Filesystem {
  readonly device?: string;
  readonly mountPoint?: string;
  readonly type?: string;
  readonly label?: string;
  readonly options?: AttributedDict;
}

/** FleetspeakValidationInfo proto mapping. */
export declare interface FleetspeakValidationInfo {
  readonly tags?: readonly FleetspeakValidationInfoTag[];
}

/** FleetspeakValidationInfoTag proto mapping. */
export declare interface FleetspeakValidationInfoTag {
  readonly key?: string;
  readonly value?: string;
}

/** FlowContext proto mapping. */
export declare interface FlowContext {
  readonly backtrace?: string;
  readonly clientResources?: ClientResources;
  readonly createTime?: RDFDatetime;
  readonly creator?: string;
  readonly currentState?: string;
  readonly killTimestamp?: RDFDatetime;
  readonly networkBytesSent?: ProtoUint64;
  readonly nextOutboundId?: ProtoUint64;
  readonly nextProcessedRequest?: ProtoUint64;
  readonly outputPluginsStates?: readonly OutputPluginState[];
  readonly outstandingRequests?: ProtoUint64;
  readonly sessionId?: SessionID;
  readonly state?: FlowContextState;
  readonly status?: string;
}

/** FlowContext.State proto mapping. */
export enum FlowContextState {
  RUNNING = 'RUNNING',
  TERMINATED = 'TERMINATED',
  ERROR = 'ERROR',
  WELL_KNOWN = 'WELL_KNOWN',
  CLIENT_CRASHED = 'CLIENT_CRASHED',
}

/** FlowLikeObjectReference proto mapping. */
export declare interface FlowLikeObjectReference {
  readonly objectType?: FlowLikeObjectReferenceObjectType;
  readonly flowReference?: FlowReference;
  readonly huntReference?: HuntReference;
}

/** FlowLikeObjectReference.ObjectType proto mapping. */
export enum FlowLikeObjectReferenceObjectType {
  UNKNOWN = 'UNKNOWN',
  FLOW_REFERENCE = 'FLOW_REFERENCE',
  HUNT_REFERENCE = 'HUNT_REFERENCE',
}

/** FlowOutputPluginLogEntry proto mapping. */
export declare interface FlowOutputPluginLogEntry {
  readonly flowId?: string;
  readonly clientId?: string;
  readonly huntId?: string;
  readonly outputPluginId?: string;
  readonly logEntryType?: FlowOutputPluginLogEntryLogEntryType;
  readonly timestamp?: RDFDatetime;
  readonly message?: string;
}

/** FlowOutputPluginLogEntry.LogEntryType proto mapping. */
export enum FlowOutputPluginLogEntryLogEntryType {
  UNSET = 'UNSET',
  LOG = 'LOG',
  ERROR = 'ERROR',
}

/** FlowReference proto mapping. */
export declare interface FlowReference {
  readonly flowId?: string;
  readonly clientId?: string;
}

/** FlowResultCount proto mapping. */
export declare interface FlowResultCount {
  readonly type?: string;
  readonly tag?: string;
  readonly count?: ProtoUint64;
}

/** FlowResultMetadata proto mapping. */
export declare interface FlowResultMetadata {
  readonly numResultsPerTypeTag?: readonly FlowResultCount[];
  readonly isMetadataSet?: boolean;
}

/** FlowRunnerArgs proto mapping. */
export declare interface FlowRunnerArgs {
  readonly clientId?: string;
  readonly cpuLimit?: ProtoUint64;
  readonly networkBytesLimit?: ProtoUint64;
  readonly requestState?: RequestState;
  readonly flowName?: string;
  readonly writeIntermediateResults?: boolean;
  readonly outputPlugins?: readonly OutputPluginDescriptor[];
  readonly originalFlow?: FlowReference;
  readonly disableRrgSupport?: boolean;
}

/** ForemanClientRule proto mapping. */
export declare interface ForemanClientRule {
  readonly ruleType?: ForemanClientRuleType;
  readonly os?: ForemanOsClientRule;
  readonly label?: ForemanLabelClientRule;
  readonly regex?: ForemanRegexClientRule;
  readonly integer?: ForemanIntegerClientRule;
}

/** ForemanClientRule.Type proto mapping. */
export enum ForemanClientRuleType {
  OS = 'OS',
  LABEL = 'LABEL',
  REGEX = 'REGEX',
  INTEGER = 'INTEGER',
}

/** ForemanClientRuleSet proto mapping. */
export declare interface ForemanClientRuleSet {
  readonly matchMode?: ForemanClientRuleSetMatchMode;
  readonly rules?: readonly ForemanClientRule[];
}

/** ForemanClientRuleSet.MatchMode proto mapping. */
export enum ForemanClientRuleSetMatchMode {
  MATCH_ALL = 'MATCH_ALL',
  MATCH_ANY = 'MATCH_ANY',
}

/** ForemanIntegerClientRule proto mapping. */
export declare interface ForemanIntegerClientRule {
  readonly operator?: ForemanIntegerClientRuleOperator;
  readonly value?: ProtoUint64;
  readonly field?: ForemanIntegerClientRuleForemanIntegerField;
}

/** ForemanIntegerClientRule.ForemanIntegerField proto mapping. */
export enum ForemanIntegerClientRuleForemanIntegerField {
  UNSET = 'UNSET',
  INSTALL_TIME = 'INSTALL_TIME',
  CLIENT_VERSION = 'CLIENT_VERSION',
  LAST_BOOT_TIME = 'LAST_BOOT_TIME',
}

/** ForemanIntegerClientRule.Operator proto mapping. */
export enum ForemanIntegerClientRuleOperator {
  EQUAL = 'EQUAL',
  LESS_THAN = 'LESS_THAN',
  GREATER_THAN = 'GREATER_THAN',
}

/** ForemanLabelClientRule proto mapping. */
export declare interface ForemanLabelClientRule {
  readonly labelNames?: readonly string[];
  readonly matchMode?: ForemanLabelClientRuleMatchMode;
}

/** ForemanLabelClientRule.MatchMode proto mapping. */
export enum ForemanLabelClientRuleMatchMode {
  MATCH_ALL = 'MATCH_ALL',
  MATCH_ANY = 'MATCH_ANY',
  DOES_NOT_MATCH_ALL = 'DOES_NOT_MATCH_ALL',
  DOES_NOT_MATCH_ANY = 'DOES_NOT_MATCH_ANY',
}

/** ForemanOsClientRule proto mapping. */
export declare interface ForemanOsClientRule {
  readonly osWindows?: boolean;
  readonly osLinux?: boolean;
  readonly osDarwin?: boolean;
}

/** ForemanRegexClientRule proto mapping. */
export declare interface ForemanRegexClientRule {
  readonly attributeRegex?: string;
  readonly field?: ForemanRegexClientRuleForemanStringField;
}

/** ForemanRegexClientRule.ForemanStringField proto mapping. */
export enum ForemanRegexClientRuleForemanStringField {
  UNSET = 'UNSET',
  USERNAMES = 'USERNAMES',
  FQDN = 'FQDN',
  HOST_IPS = 'HOST_IPS',
  CLIENT_NAME = 'CLIENT_NAME',
  CLIENT_DESCRIPTION = 'CLIENT_DESCRIPTION',
  SYSTEM = 'SYSTEM',
  MAC_ADDRESSES = 'MAC_ADDRESSES',
  KERNEL_VERSION = 'KERNEL_VERSION',
  OS_VERSION = 'OS_VERSION',
  OS_RELEASE = 'OS_RELEASE',
  CLIENT_LABELS = 'CLIENT_LABELS',
  CLIENT_ID = 'CLIENT_ID',
}

/** GUISettings proto mapping. */
export declare interface GUISettings {
  readonly mode?: GUISettingsUIMode;
  readonly canaryMode?: boolean;
}

/** GUISettings.UIMode proto mapping. */
export enum GUISettingsUIMode {
  BASIC = 'BASIC',
  ADVANCED = 'ADVANCED',
  DEBUG = 'DEBUG',
}

/** GetCrowdstrikeAgentIdResult proto mapping. */
export declare interface GetCrowdstrikeAgentIdResult {
  readonly agentId?: string;
}

/** GetMBRArgs proto mapping. */
export declare interface GetMBRArgs {
  readonly length?: ProtoUint64;
}

/** GetMBRStore proto mapping. */
export declare interface GetMBRStore {
  readonly bytesDownloaded?: ProtoUint64;
  readonly buffers?: readonly ProtoBytes[];
}

/** GetMemorySizeResult proto mapping. */
export declare interface GetMemorySizeResult {
  readonly totalBytes?: ProtoUint64;
}

/** GlobComponentExplanation proto mapping. */
export declare interface GlobComponentExplanation {
  readonly globExpression?: string;
  readonly examples?: readonly string[];
}

/** GoogleCloudInstance proto mapping. */
export declare interface GoogleCloudInstance {
  readonly uniqueId?: string;
  readonly zone?: string;
  readonly projectId?: string;
  readonly instanceId?: string;
  readonly hostname?: string;
  readonly machineType?: string;
}

/** GrrMessage proto mapping. */
export declare interface GrrMessage {
  readonly sessionId?: string;
  readonly requestId?: ProtoUint64;
  readonly responseId?: ProtoUint64;
  readonly name?: string;
  readonly payloadAny?: Any;
  readonly args?: ProtoBytes;
  readonly source?: RDFURN;
  readonly authState?: GrrMessageAuthorizationState;
  readonly type?: GrrMessageType;
  readonly ttl?: ProtoUint32;
  readonly cpuLimit?: ProtoFloat;
  readonly argsRdfName?: string;
  readonly taskId?: ProtoUint64;
  readonly taskTtl?: ProtoInt32;
  readonly queue?: RDFURN;
  readonly leasedUntil?: RDFDatetime;
  readonly leasedBy?: string;
  readonly networkBytesLimit?: ProtoUint64;
  readonly timestamp?: RDFDatetime;
  readonly runtimeLimitUs?: Duration;
}

/** GrrMessage.AuthorizationState proto mapping. */
export enum GrrMessageAuthorizationState {
  UNAUTHENTICATED = 'UNAUTHENTICATED',
  AUTHENTICATED = 'AUTHENTICATED',
  DESYNCHRONIZED = 'DESYNCHRONIZED',
}

/** GrrMessage.Type proto mapping. */
export enum GrrMessageType {
  MESSAGE = 'MESSAGE',
  STATUS = 'STATUS',
  ITERATOR = 'ITERATOR',
}

/** GrrStatus proto mapping. */
export declare interface GrrStatus {
  readonly status?: GrrStatusReturnedStatus;
  readonly errorMessage?: string;
  readonly backtrace?: string;
  readonly cpuTimeUsed?: CpuSeconds;
  readonly childSessionId?: SessionID;
  readonly networkBytesSent?: ProtoUint64;
  readonly runtimeUs?: Duration;
}

/** GrrStatus.ReturnedStatus proto mapping. */
export enum GrrStatusReturnedStatus {
  OK = 'OK',
  IOERROR = 'IOERROR',
  RETRANSMISSION_DETECTED = 'RETRANSMISSION_DETECTED',
  CLIENT_KILLED = 'CLIENT_KILLED',
  NETWORK_LIMIT_EXCEEDED = 'NETWORK_LIMIT_EXCEEDED',
  RUNTIME_LIMIT_EXCEEDED = 'RUNTIME_LIMIT_EXCEEDED',
  CPU_LIMIT_EXCEEDED = 'CPU_LIMIT_EXCEEDED',
  WORKER_STUCK = 'WORKER_STUCK',
  GENERIC_ERROR = 'GENERIC_ERROR',
}

/** HardwareInfo proto mapping. */
export declare interface HardwareInfo {
  readonly serialNumber?: string;
  readonly systemManufacturer?: string;
  readonly systemProductName?: string;
  readonly systemUuid?: string;
  readonly systemSkuNumber?: string;
  readonly systemFamily?: string;
  readonly biosVendor?: string;
  readonly biosVersion?: string;
  readonly biosReleaseDate?: string;
  readonly biosRomSize?: string;
  readonly biosRevision?: string;
  readonly systemAssettag?: string;
}

/** Hash proto mapping. */
export declare interface Hash {
  readonly sha256?: HashDigest;
  readonly sha1?: HashDigest;
  readonly md5?: HashDigest;
  readonly pecoffSha1?: HashDigest;
  readonly pecoffMd5?: HashDigest;
  readonly pecoffSha256?: HashDigest;
  readonly signedData?: readonly AuthenticodeSignedData[];
  readonly numBytes?: ProtoUint64;
  readonly sourceOffset?: ProtoUint64;
}

/** HashMultipleFilesArgs proto mapping. */
export declare interface HashMultipleFilesArgs {
  readonly pathExpressions?: readonly GlobExpression[];
  readonly modificationTime?: FileFinderModificationTimeCondition;
  readonly accessTime?: FileFinderAccessTimeCondition;
  readonly inodeChangeTime?: FileFinderInodeChangeTimeCondition;
  readonly size?: FileFinderSizeCondition;
  readonly extFlags?: FileFinderExtFlagsCondition;
  readonly contentsRegexMatch?: FileFinderContentsRegexMatchCondition;
  readonly contentsLiteralMatch?: FileFinderContentsLiteralMatchCondition;
}

/** HashMultipleFilesProgress proto mapping. */
export declare interface HashMultipleFilesProgress {
  readonly numFound?: ProtoUint64;
  readonly numInProgress?: ProtoUint64;
  readonly numRawFsAccessRetries?: ProtoUint64;
  readonly numHashed?: ProtoUint64;
  readonly numFailed?: ProtoUint64;
}

/** HuntContext proto mapping. */
export declare interface HuntContext {
  readonly clientResources?: ClientResources;
  readonly createTime?: RDFDatetime;
  readonly creator?: string;
  readonly deprecatedExpires?: RDFDatetime;
  readonly duration?: DurationSeconds;
  readonly networkBytesSent?: ProtoUint64;
  readonly nextClientDue?: RDFDatetime;
  readonly nextOutboundId?: ProtoUint64;
  readonly nextProcessedRequest?: ProtoUint64;
  readonly sessionId?: SessionID;
  readonly startTime?: RDFDatetime;
  readonly usageStats?: ClientResourcesStats;
}

/** HuntCronAction proto mapping. */
export declare interface HuntCronAction {
  readonly huntRunnerArgs?: HuntRunnerArgs;
  readonly flowName?: string;
  readonly flowArgs?: ProtoBytes;
}

/** HuntReference proto mapping. */
export declare interface HuntReference {
  readonly huntId?: string;
}

/** HuntRunnerArgs proto mapping. */
export declare interface HuntRunnerArgs {
  readonly huntName?: string;
  readonly description?: string;
  readonly clientRuleSet?: ForemanClientRuleSet;
  readonly cpuLimit?: ProtoUint64;
  readonly networkBytesLimit?: ProtoUint64;
  readonly clientLimit?: ProtoUint64;
  readonly crashLimit?: ProtoUint64;
  readonly avgResultsPerClientLimit?: ProtoUint64;
  readonly avgCpuSecondsPerClientLimit?: ProtoUint64;
  readonly avgNetworkBytesPerClientLimit?: ProtoUint64;
  readonly expiryTime?: DurationSeconds;
  readonly clientRate?: ProtoFloat;
  readonly crashAlertEmail?: string;
  readonly outputPlugins?: readonly OutputPluginDescriptor[];
  readonly perClientCpuLimit?: ProtoUint64;
  readonly perClientNetworkLimitBytes?: ProtoUint64;
  readonly originalObject?: FlowLikeObjectReference;
}

/** IndexToBufferReference proto mapping. */
export declare interface IndexToBufferReference {
  readonly index?: ProtoUint64;
  readonly bufferReference?: BufferReference;
}

/** IndexToTracker proto mapping. */
export declare interface IndexToTracker {
  readonly index?: ProtoUint64;
  readonly tracker?: MultiGetFileTracker;
}

/** Interface proto mapping. */
export declare interface Interface {
  readonly macAddress?: ProtoBytes;
  readonly ifname?: string;
  readonly addresses?: readonly NetworkAddress[];
}

/** InterrogateArgs proto mapping. */
export declare interface InterrogateArgs {
  readonly lightweight?: boolean;
}

/** InterrogateStore proto mapping. */
export declare interface InterrogateStore {
  readonly clientSnapshot?: ClientSnapshot;
  readonly fqdn?: string;
  readonly os?: string;
}

/** KeyValue proto mapping. */
export declare interface KeyValue {
  readonly k?: DataBlob;
  readonly v?: DataBlob;
}

/** KnowledgeBase proto mapping. */
export declare interface KnowledgeBase {
  readonly users?: readonly User[];
  readonly fqdn?: string;
  readonly timeZone?: string;
  readonly os?: string;
  readonly osMajorVersion?: ProtoUint32;
  readonly osMinorVersion?: ProtoUint32;
  readonly environPath?: string;
  readonly environTemp?: string;
  readonly osRelease?: string;
  readonly environAllusersappdata?: string;
  readonly environAllusersprofile?: string;
  readonly environCommonprogramfiles?: string;
  readonly environCommonprogramfilesx86?: string;
  readonly environComspec?: string;
  readonly environDriverdata?: string;
  readonly environProfilesdirectory?: string;
  readonly environProgramfiles?: string;
  readonly environProgramdata?: string;
  readonly environProgramfilesx86?: string;
  readonly environSystemdrive?: string;
  readonly environSystemroot?: string;
  readonly environWindir?: string;
  readonly currentControlSet?: string;
  readonly codePage?: string;
  readonly domain?: string;
  readonly deprecatedUsers?: readonly ProtoBytes[];
}

/** KnowledgeBaseInitializationArgs proto mapping. */
export declare interface KnowledgeBaseInitializationArgs {
  readonly requireComplete?: boolean;
  readonly lightweight?: boolean;
}

/** KnowledgeBaseInitializationStore proto mapping. */
export declare interface KnowledgeBaseInitializationStore {
  readonly knowledgeBase?: KnowledgeBase;
}

/** LaunchBinaryArgs proto mapping. */
export declare interface LaunchBinaryArgs {
  readonly binary?: RDFURN;
  readonly commandLine?: string;
}

/** LaunchBinaryStore proto mapping. */
export declare interface LaunchBinaryStore {
  readonly writePath?: string;
}

/** ListContainersFlowArgs proto mapping. */
export declare interface ListContainersFlowArgs {
  readonly inspectHostroot?: boolean;
}

/** ListContainersFlowResult proto mapping. */
export declare interface ListContainersFlowResult {
  readonly containers?: readonly ContainerDetails[];
}

/** ListDirectoryArgs proto mapping. */
export declare interface ListDirectoryArgs {
  readonly pathspec?: PathSpec;
}

/** ListDirectoryStore proto mapping. */
export declare interface ListDirectoryStore {
  readonly urn?: string;
  readonly statEntry?: StatEntry;
  readonly symlinkDepth?: ProtoUint32;
}

/** ListNamedPipesFlowArgs proto mapping. */
export declare interface ListNamedPipesFlowArgs {
  readonly pipeNameRegex?: string;
  readonly procExeRegex?: string;
  readonly pipeTypeFilter?: ListNamedPipesFlowArgsPipeTypeFilter;
  readonly pipeEndFilter?: ListNamedPipesFlowArgsPipeEndFilter;
}

/** ListNamedPipesFlowArgs.PipeEndFilter proto mapping. */
export enum ListNamedPipesFlowArgsPipeEndFilter {
  ANY_END = 'ANY_END',
  CLIENT_END = 'CLIENT_END',
  SERVER_END = 'SERVER_END',
}

/** ListNamedPipesFlowArgs.PipeTypeFilter proto mapping. */
export enum ListNamedPipesFlowArgsPipeTypeFilter {
  ANY_TYPE = 'ANY_TYPE',
  BYTE_TYPE = 'BYTE_TYPE',
  MESSAGE_TYPE = 'MESSAGE_TYPE',
}

/** ListNamedPipesFlowResult proto mapping. */
export declare interface ListNamedPipesFlowResult {
  readonly pipe?: NamedPipe;
  readonly proc?: Process;
}

/** ListNamedPipesFlowStore proto mapping. */
export declare interface ListNamedPipesFlowStore {
  readonly pipes?: readonly NamedPipe[];
}

/** ListProcessesArgs proto mapping. */
export declare interface ListProcessesArgs {
  readonly filenameRegex?: string;
  readonly fetchBinaries?: boolean;
  readonly connectionStates?: readonly NetworkConnectionState[];
  readonly pids?: readonly ProtoUint32[];
}

/** MultiGetFileArgs proto mapping. */
export declare interface MultiGetFileArgs {
  readonly pathspecs?: readonly PathSpec[];
  readonly useExternalStores?: boolean;
  readonly fileSize?: ByteSize;
  readonly maximumPendingFiles?: ProtoUint64;
  readonly stopAt?: MultiGetFileArgsStopAt;
}

/** MultiGetFileArgs.StopAt proto mapping. */
export enum MultiGetFileArgsStopAt {
  NOTHING = 'NOTHING',
  STAT = 'STAT',
  HASH = 'HASH',
}

/** MultiGetFileProgress proto mapping. */
export declare interface MultiGetFileProgress {
  readonly numPendingHashes?: ProtoUint32;
  readonly numPendingFiles?: ProtoUint32;
  readonly numSkipped?: ProtoUint32;
  readonly numCollected?: ProtoUint32;
  readonly numFailed?: ProtoUint32;
  readonly pathspecsProgress?: readonly PathSpecProgress[];
}

/** MultiGetFileStore proto mapping. */
export declare interface MultiGetFileStore {
  readonly numFilesToFetch?: ProtoUint64;
  readonly numFilesHashed?: ProtoUint64;
  readonly numFilesFetched?: ProtoUint64;
  readonly numFilesSkipped?: ProtoUint64;
  readonly numFilesFailed?: ProtoUint64;
  readonly numFilesHashedSinceCheck?: ProtoUint64;
  readonly nextPathspecToStart?: ProtoUint64;
  readonly blobHashesPending?: ProtoUint64;
  readonly pendingStats?: readonly IndexToTracker[];
  readonly pendingHashes?: readonly IndexToTracker[];
  readonly pendingFiles?: readonly IndexToTracker[];
  readonly indexedPathspecs?: readonly PathSpec[];
  readonly pathspecsProgress?: readonly PathSpecProgress[];
}

/** MultiGetFileTracker proto mapping. */
export declare interface MultiGetFileTracker {
  readonly index?: ProtoUint64;
  readonly statEntry?: StatEntry;
  readonly hashObj?: Hash;
  readonly hashList?: readonly BufferReference[];
  readonly indexToBuffers?: readonly IndexToBufferReference[];
  readonly bytesRead?: ProtoUint64;
  readonly sizeToDownload?: ProtoUint64;
  readonly expectedChunks?: ProtoUint64;
}

/** NamedPipe proto mapping. */
export declare interface NamedPipe {
  readonly name?: string;
  readonly serverPid?: ProtoUint32;
  readonly clientPid?: ProtoUint32;
  readonly clientComputerName?: string;
  readonly clientUserName?: string;
  readonly flags?: ProtoUint32;
  readonly curInstanceCount?: ProtoUint32;
  readonly maxInstanceCount?: ProtoUint32;
  readonly inBufferSize?: ProtoUint32;
  readonly outBufferSize?: ProtoUint32;
}

/** NetstatArgs proto mapping. */
export declare interface NetstatArgs {
  readonly listeningOnly?: boolean;
}

/** NetworkAddress proto mapping. */
export declare interface NetworkAddress {
  readonly addressType?: NetworkAddressFamily;
  readonly deprecatedHumanReadable?: string;
  readonly packedBytes?: ProtoBytes;
}

/** NetworkAddress.Family proto mapping. */
export enum NetworkAddressFamily {
  INET = 'INET',
  INET6 = 'INET6',
}

/** NetworkConnection proto mapping. */
export declare interface NetworkConnection {
  readonly family?: NetworkConnectionFamily;
  readonly type?: NetworkConnectionType;
  readonly localAddress?: NetworkEndpoint;
  readonly remoteAddress?: NetworkEndpoint;
  readonly state?: NetworkConnectionState;
  readonly pid?: ProtoUint32;
  readonly ctime?: ProtoUint64;
  readonly processName?: string;
}

/** NetworkConnection.Family proto mapping. */
export enum NetworkConnectionFamily {
  INET = 'INET',
  INET6 = 'INET6',
}

/** NetworkConnection.State proto mapping. */
export enum NetworkConnectionState {
  UNKNOWN = 'UNKNOWN',
  CLOSED = 'CLOSED',
  LISTEN = 'LISTEN',
  SYN_SENT = 'SYN_SENT',
  SYN_RECV = 'SYN_RECV',
  ESTABLISHED = 'ESTABLISHED',
  FIN_WAIT1 = 'FIN_WAIT1',
  FIN_WAIT2 = 'FIN_WAIT2',
  CLOSE_WAIT = 'CLOSE_WAIT',
  CLOSING = 'CLOSING',
  LAST_ACK = 'LAST_ACK',
  TIME_WAIT = 'TIME_WAIT',
  DELETE_TCB = 'DELETE_TCB',
  NONE = 'NONE',
  CLOSE = 'CLOSE',
}

/** NetworkConnection.Type proto mapping. */
export enum NetworkConnectionType {
  UNKNOWN_SOCKET = 'UNKNOWN_SOCKET',
  SOCK_STREAM = 'SOCK_STREAM',
  SOCK_DGRAM = 'SOCK_DGRAM',
}

/** NetworkEndpoint proto mapping. */
export declare interface NetworkEndpoint {
  readonly ip?: string;
  readonly port?: ProtoInt32;
}

/** OSXServiceInformation proto mapping. */
export declare interface OSXServiceInformation {
  readonly label?: string;
  readonly program?: string;
  readonly args?: readonly string[];
  readonly pid?: ProtoUint64;
  readonly sessiontype?: string;
  readonly lastexitstatus?: ProtoUint64;
  readonly timeout?: ProtoUint64;
  readonly ondemand?: boolean;
  readonly machservice?: readonly string[];
  readonly perjobmachservice?: readonly string[];
  readonly socket?: readonly string[];
  readonly plist?: RDFURN;
}

/** OnlineNotificationArgs proto mapping. */
export declare interface OnlineNotificationArgs {
  readonly email?: string;
}

/** OsqueryColumn proto mapping. */
export declare interface OsqueryColumn {
  readonly name?: string;
  readonly type?: OsqueryType;
}

/** OsqueryFlowArgs proto mapping. */
export declare interface OsqueryFlowArgs {
  readonly query?: string;
  readonly timeoutMillis?: ProtoUint64;
  readonly ignoreStderrErrors?: boolean;
  readonly fileCollectionColumns?: readonly string[];
  readonly configurationPath?: string;
  readonly configurationContent?: string;
}

/** OsqueryHeader proto mapping. */
export declare interface OsqueryHeader {
  readonly columns?: readonly OsqueryColumn[];
}

/** OsqueryProgress proto mapping. */
export declare interface OsqueryProgress {
  readonly partialTable?: OsqueryTable;
  readonly totalRowCount?: ProtoUint64;
  readonly errorMessage?: string;
}

/** OsqueryResult proto mapping. */
export declare interface OsqueryResult {
  readonly table?: OsqueryTable;
}

/** OsqueryRow proto mapping. */
export declare interface OsqueryRow {
  readonly values?: readonly string[];
}

/** OsqueryStore proto mapping. */
export declare interface OsqueryStore {
  readonly totalCollectedBytes?: ProtoUint64;
}

/** OsqueryTable proto mapping. */
export declare interface OsqueryTable {
  readonly query?: string;
  readonly header?: OsqueryHeader;
  readonly rows?: readonly OsqueryRow[];
}

/** OsqueryType proto mapping. */
export enum OsqueryType {
  UNKNOWN = 'UNKNOWN',
  TEXT = 'TEXT',
  INTEGER = 'INTEGER',
  BIGINT = 'BIGINT',
  UNSIGNED_BIGINT = 'UNSIGNED_BIGINT',
  DOUBLE = 'DOUBLE',
  BLOB = 'BLOB',
}

/** OutputPluginBatchProcessingStatus proto mapping. */
export declare interface OutputPluginBatchProcessingStatus {
  readonly status?: OutputPluginBatchProcessingStatusStatus;
  readonly pluginDescriptor?: OutputPluginDescriptor;
  readonly summary?: string;
  readonly batchIndex?: ProtoUint64;
  readonly batchSize?: ProtoUint64;
}

/** OutputPluginBatchProcessingStatus.Status proto mapping. */
export enum OutputPluginBatchProcessingStatusStatus {
  SUCCESS = 'SUCCESS',
  ERROR = 'ERROR',
}

/** OutputPluginDescriptor proto mapping. */
export declare interface OutputPluginDescriptor {
  readonly pluginName?: string;
  readonly deprecatedPluginArgs?: ProtoBytes;
  readonly args?: Any;
}

/** OutputPluginState proto mapping. */
export declare interface OutputPluginState {
  readonly pluginDescriptor?: OutputPluginDescriptor;
  readonly pluginState?: AttributedDict;
  readonly pluginId?: string;
}

/** PathInfo proto mapping. */
export declare interface PathInfo {
  readonly pathType?: PathInfoPathType;
  readonly components?: readonly string[];
  readonly timestamp?: RDFDatetime;
  readonly lastStatEntryTimestamp?: RDFDatetime;
  readonly lastHashEntryTimestamp?: RDFDatetime;
  readonly directory?: boolean;
  readonly statEntry?: StatEntry;
  readonly hashEntry?: Hash;
}

/** PathInfo.PathType proto mapping. */
export enum PathInfoPathType {
  UNSET = 'UNSET',
  OS = 'OS',
  TSK = 'TSK',
  REGISTRY = 'REGISTRY',
  TEMP = 'TEMP',
  NTFS = 'NTFS',
}

/** PathSpec proto mapping. */
export declare interface PathSpec {
  readonly pathtype?: PathSpecPathType;
  readonly path?: string;
  readonly mountPoint?: string;
  readonly streamName?: string;
  readonly nestedPath?: PathSpec;
  readonly offset?: ProtoUint64;
  readonly pathOptions?: PathSpecOptions;
  readonly recursionDepth?: ProtoUint64;
  readonly inode?: ProtoUint64;
  readonly ntfsType?: PathSpecTskFsAttrType;
  readonly ntfsId?: ProtoUint64;
  readonly fileSizeOverride?: ByteSize;
  readonly isVirtualroot?: boolean;
  readonly implementationType?: PathSpecImplementationType;
}

/** PathSpec.ImplementationType proto mapping. */
export enum PathSpecImplementationType {
  DEFAULT = 'DEFAULT',
  DIRECT = 'DIRECT',
  SANDBOX = 'SANDBOX',
}

/** PathSpec.Options proto mapping. */
export enum PathSpecOptions {
  CASE_INSENSITIVE = 'CASE_INSENSITIVE',
  CASE_LITERAL = 'CASE_LITERAL',
  REGEX = 'REGEX',
  RECURSIVE = 'RECURSIVE',
}

/** PathSpec.PathType proto mapping. */
export enum PathSpecPathType {
  UNSET = 'UNSET',
  OS = 'OS',
  TSK = 'TSK',
  REGISTRY = 'REGISTRY',
  TMPFILE = 'TMPFILE',
  NTFS = 'NTFS',
}

/** PathSpec.tsk_fs_attr_type proto mapping. */
export enum PathSpecTskFsAttrType {
  TSK_FS_ATTR_TYPE_DEFAULT = 'TSK_FS_ATTR_TYPE_DEFAULT',
  TSK_FS_ATTR_TYPE_NTFS_SI = 'TSK_FS_ATTR_TYPE_NTFS_SI',
  TSK_FS_ATTR_TYPE_NTFS_ATTRLIST = 'TSK_FS_ATTR_TYPE_NTFS_ATTRLIST',
  TSK_FS_ATTR_TYPE_NTFS_FNAME = 'TSK_FS_ATTR_TYPE_NTFS_FNAME',
  TSK_FS_ATTR_TYPE_NTFS_VVER = 'TSK_FS_ATTR_TYPE_NTFS_VVER',
  TSK_FS_ATTR_TYPE_NTFS_OBJID = 'TSK_FS_ATTR_TYPE_NTFS_OBJID',
  TSK_FS_ATTR_TYPE_NTFS_SEC = 'TSK_FS_ATTR_TYPE_NTFS_SEC',
  TSK_FS_ATTR_TYPE_NTFS_VNAME = 'TSK_FS_ATTR_TYPE_NTFS_VNAME',
  TSK_FS_ATTR_TYPE_NTFS_VINFO = 'TSK_FS_ATTR_TYPE_NTFS_VINFO',
  TSK_FS_ATTR_TYPE_NTFS_DATA = 'TSK_FS_ATTR_TYPE_NTFS_DATA',
  TSK_FS_ATTR_TYPE_NTFS_IDXROOT = 'TSK_FS_ATTR_TYPE_NTFS_IDXROOT',
  TSK_FS_ATTR_TYPE_NTFS_IDXALLOC = 'TSK_FS_ATTR_TYPE_NTFS_IDXALLOC',
  TSK_FS_ATTR_TYPE_NTFS_BITMAP = 'TSK_FS_ATTR_TYPE_NTFS_BITMAP',
  TSK_FS_ATTR_TYPE_NTFS_SYMLNK = 'TSK_FS_ATTR_TYPE_NTFS_SYMLNK',
  TSK_FS_ATTR_TYPE_NTFS_REPARSE = 'TSK_FS_ATTR_TYPE_NTFS_REPARSE',
  TSK_FS_ATTR_TYPE_NTFS_EAINFO = 'TSK_FS_ATTR_TYPE_NTFS_EAINFO',
  TSK_FS_ATTR_TYPE_NTFS_EA = 'TSK_FS_ATTR_TYPE_NTFS_EA',
  TSK_FS_ATTR_TYPE_NTFS_PROP = 'TSK_FS_ATTR_TYPE_NTFS_PROP',
  TSK_FS_ATTR_TYPE_NTFS_LOG = 'TSK_FS_ATTR_TYPE_NTFS_LOG',
  TSK_FS_ATTR_TYPE_UNIX_INDIR = 'TSK_FS_ATTR_TYPE_UNIX_INDIR',
}

/** PathSpecProgress proto mapping. */
export declare interface PathSpecProgress {
  readonly pathspec?: PathSpec;
  readonly status?: PathSpecProgressStatus;
}

/** PathSpecProgress.Status proto mapping. */
export enum PathSpecProgressStatus {
  UNDEFINED = 'UNDEFINED',
  IN_PROGRESS = 'IN_PROGRESS',
  SKIPPED = 'SKIPPED',
  COLLECTED = 'COLLECTED',
  FAILED = 'FAILED',
}

/** Process proto mapping. */
export declare interface Process {
  readonly pid?: ProtoUint32;
  readonly ppid?: ProtoUint32;
  readonly name?: string;
  readonly exe?: string;
  readonly cmdline?: readonly string[];
  readonly ctime?: ProtoUint64;
  readonly realUid?: ProtoUint32;
  readonly effectiveUid?: ProtoUint32;
  readonly savedUid?: ProtoUint32;
  readonly realGid?: ProtoUint32;
  readonly effectiveGid?: ProtoUint32;
  readonly savedGid?: ProtoUint32;
  readonly username?: string;
  readonly terminal?: string;
  readonly status?: string;
  readonly nice?: ProtoInt32;
  readonly cwd?: string;
  readonly numThreads?: ProtoUint32;
  readonly userCpuTime?: ProtoFloat;
  readonly systemCpuTime?: ProtoFloat;
  readonly rssSize?: ProtoUint64;
  readonly vmsSize?: ProtoUint64;
  readonly memoryPercent?: ProtoFloat;
  readonly openFiles?: readonly string[];
  readonly connections?: readonly NetworkConnection[];
}

/** ProcessMemoryError proto mapping. */
export declare interface ProcessMemoryError {
  readonly process?: Process;
  readonly error?: string;
}

/** ProcessMemoryRegion proto mapping. */
export declare interface ProcessMemoryRegion {
  readonly start?: ProtoUint64;
  readonly size?: ProtoUint64;
  readonly file?: PathSpec;
  readonly isExecutable?: boolean;
  readonly isWritable?: boolean;
  readonly isReadable?: boolean;
  readonly dumpedSize?: ProtoUint64;
}

/** PwEntry proto mapping. */
export declare interface PwEntry {
  readonly store?: PwEntryPwStore;
  readonly hashType?: PwEntryPwHash;
  readonly age?: ProtoUint32;
  readonly maxAge?: ProtoUint32;
}

/** PwEntry.PwHash proto mapping. */
export enum PwEntryPwHash {
  DES = 'DES',
  MD5 = 'MD5',
  BLOWFISH = 'BLOWFISH',
  NTHASH = 'NTHASH',
  UNUSED = 'UNUSED',
  SHA256 = 'SHA256',
  SHA512 = 'SHA512',
  UNSET = 'UNSET',
  DISABLED = 'DISABLED',
  EMPTY = 'EMPTY',
}

/** PwEntry.PwStore proto mapping. */
export enum PwEntryPwStore {
  UNKNOWN = 'UNKNOWN',
  PASSWD = 'PASSWD',
  SHADOW = 'SHADOW',
  GROUP = 'GROUP',
  GSHADOW = 'GSHADOW',
}

/** ReadLowLevelArgs proto mapping. */
export declare interface ReadLowLevelArgs {
  readonly path?: string;
  readonly length?: ByteSize;
  readonly offset?: ProtoUint64;
  readonly sectorBlockSize?: ProtoUint64;
}

/** ReadLowLevelFlowResult proto mapping. */
export declare interface ReadLowLevelFlowResult {
  readonly path?: string;
}

/** RecursiveListDirectoryArgs proto mapping. */
export declare interface RecursiveListDirectoryArgs {
  readonly pathspec?: PathSpec;
  readonly maxDepth?: ProtoUint64;
}

/** RecursiveListDirectoryProgress proto mapping. */
export declare interface RecursiveListDirectoryProgress {
  readonly dirCount?: ProtoUint64;
  readonly fileCount?: ProtoUint64;
}

/** RecursiveListDirectoryStore proto mapping. */
export declare interface RecursiveListDirectoryStore {
  readonly firstDirectory?: string;
}

/** RegistryFinderArgs proto mapping. */
export declare interface RegistryFinderArgs {
  readonly keysPaths?: readonly GlobExpression[];
  readonly conditions?: readonly RegistryFinderCondition[];
}

/** RegistryFinderCondition proto mapping. */
export declare interface RegistryFinderCondition {
  readonly conditionType?: RegistryFinderConditionType;
  readonly valueLiteralMatch?: FileFinderContentsLiteralMatchCondition;
  readonly valueRegexMatch?: FileFinderContentsRegexMatchCondition;
  readonly modificationTime?: FileFinderModificationTimeCondition;
  readonly size?: FileFinderSizeCondition;
}

/** RegistryFinderCondition.Type proto mapping. */
export enum RegistryFinderConditionType {
  VALUE_LITERAL_MATCH = 'VALUE_LITERAL_MATCH',
  VALUE_REGEX_MATCH = 'VALUE_REGEX_MATCH',
  MODIFICATION_TIME = 'MODIFICATION_TIME',
  SIZE = 'SIZE',
}

/** RequestState proto mapping. */
export declare interface RequestState {
  readonly id?: ProtoUint32;
  readonly tsId?: ProtoUint64;
  readonly nextState?: string;
  readonly status?: GrrStatus;
  readonly data?: Dict;
  readonly responseCount?: ProtoUint32;
  readonly transmissionCount?: ProtoUint32;
  readonly clientId?: string;
  readonly sessionId?: SessionID;
  readonly request?: GrrMessage;
}

/** RunningStats proto mapping. */
export declare interface RunningStats {
  readonly histogram?: StatsHistogram;
  readonly num?: ProtoUint64;
  readonly sum?: ProtoDouble;
  readonly stddev?: ProtoDouble;
}

/** SampleFloat proto mapping. */
export declare interface SampleFloat {
  readonly label?: string;
  readonly xValue?: ProtoFloat;
  readonly yValue?: ProtoFloat;
}

/** SoftwarePackage proto mapping. */
export declare interface SoftwarePackage {
  readonly name?: string;
  readonly version?: string;
  readonly architecture?: string;
  readonly publisher?: string;
  readonly installState?: SoftwarePackageInstallState;
  readonly description?: string;
  readonly installedOn?: ProtoUint64;
  readonly installedBy?: string;
  readonly epoch?: ProtoUint32;
  readonly sourceRpm?: string;
  readonly sourceDeb?: string;
}

/** SoftwarePackage.InstallState proto mapping. */
export enum SoftwarePackageInstallState {
  INSTALLED = 'INSTALLED',
  PENDING = 'PENDING',
  UNINSTALLED = 'UNINSTALLED',
  UNKNOWN = 'UNKNOWN',
}

/** SoftwarePackages proto mapping. */
export declare interface SoftwarePackages {
  readonly packages?: readonly SoftwarePackage[];
}

/** StartupInfo proto mapping. */
export declare interface StartupInfo {
  readonly clientInfo?: ClientInformation;
  readonly bootTime?: RDFDatetime;
  readonly interrogateRequested?: boolean;
  readonly timestamp?: RDFDatetime;
}

/** StatEntry proto mapping. */
export declare interface StatEntry {
  readonly stMode?: ProtoUint64;
  readonly stIno?: ProtoUint64;
  readonly stDev?: ProtoUint64;
  readonly stNlink?: ProtoUint64;
  readonly stUid?: ProtoUint32;
  readonly stGid?: ProtoUint32;
  readonly stSize?: ProtoUint64;
  readonly stAtime?: RDFDatetimeSeconds;
  readonly stMtime?: RDFDatetimeSeconds;
  readonly stCtime?: RDFDatetimeSeconds;
  readonly stBlocks?: ProtoUint64;
  readonly stBlksize?: ProtoUint64;
  readonly stRdev?: ProtoUint64;
  readonly stFlagsOsx?: ProtoUint32;
  readonly stFlagsLinux?: ProtoUint32;
  readonly symlink?: string;
  readonly registryType?: StatEntryRegistryType;
  readonly resident?: ProtoBytes;
  readonly pathspec?: PathSpec;
  readonly registryData?: DataBlob;
  readonly stBtime?: RDFDatetimeSeconds;
  readonly extAttrs?: readonly StatEntryExtAttr[];
}

/** StatEntry.ExtAttr proto mapping. */
export declare interface StatEntryExtAttr {
  readonly name?: ProtoBytes;
  readonly value?: ProtoBytes;
}

/** StatEntry.RegistryType proto mapping. */
export enum StatEntryRegistryType {
  REG_NONE = 'REG_NONE',
  REG_SZ = 'REG_SZ',
  REG_EXPAND_SZ = 'REG_EXPAND_SZ',
  REG_BINARY = 'REG_BINARY',
  REG_DWORD = 'REG_DWORD',
  REG_DWORD_LITTLE_ENDIAN = 'REG_DWORD_LITTLE_ENDIAN',
  REG_DWORD_BIG_ENDIAN = 'REG_DWORD_BIG_ENDIAN',
  REG_LINK = 'REG_LINK',
  REG_MULTI_SZ = 'REG_MULTI_SZ',
  REG_QWORD = 'REG_QWORD',
}

/** StatMultipleFilesArgs proto mapping. */
export declare interface StatMultipleFilesArgs {
  readonly pathExpressions?: readonly GlobExpression[];
  readonly modificationTime?: FileFinderModificationTimeCondition;
  readonly accessTime?: FileFinderAccessTimeCondition;
  readonly inodeChangeTime?: FileFinderInodeChangeTimeCondition;
  readonly size?: FileFinderSizeCondition;
  readonly extFlags?: FileFinderExtFlagsCondition;
  readonly contentsRegexMatch?: FileFinderContentsRegexMatchCondition;
  readonly contentsLiteralMatch?: FileFinderContentsLiteralMatchCondition;
}

/** StatsHistogram proto mapping. */
export declare interface StatsHistogram {
  readonly bins?: readonly StatsHistogramBin[];
}

/** StatsHistogramBin proto mapping. */
export declare interface StatsHistogramBin {
  readonly rangeMaxValue?: ProtoFloat;
  readonly num?: ProtoUint64;
}

/** StringMapEntry proto mapping. */
export declare interface StringMapEntry {
  readonly key?: string;
  readonly value?: string;
}

/** SystemCronAction proto mapping. */
export declare interface SystemCronAction {
  readonly jobClassName?: string;
}

/** TimelineArgs proto mapping. */
export declare interface TimelineArgs {
  readonly root?: ProtoBytes;
}

/** TimelineProgress proto mapping. */
export declare interface TimelineProgress {
  readonly totalEntryCount?: ProtoUint64;
}

/** TimelineResult proto mapping. */
export declare interface TimelineResult {
  readonly entryBatchBlobIds?: readonly ProtoBytes[];
  readonly entryCount?: ProtoUint64;
  readonly filesystemType?: string;
}

/** Uname proto mapping. */
export declare interface Uname {
  readonly system?: string;
  readonly node?: string;
  readonly release?: string;
  readonly version?: string;
  readonly machine?: string;
  readonly kernel?: string;
  readonly fqdn?: string;
  readonly installDate?: RDFDatetime;
  readonly libcVer?: string;
  readonly architecture?: string;
  readonly pep425tag?: string;
}

/** UnixVolume proto mapping. */
export declare interface UnixVolume {
  readonly mountPoint?: string;
  readonly options?: string;
}

/** UpdateClientArgs proto mapping. */
export declare interface UpdateClientArgs {
  readonly binaryPath?: string;
}

/** UpdateClientStore proto mapping. */
export declare interface UpdateClientStore {
  readonly writePath?: string;
}

/** User proto mapping. */
export declare interface User {
  readonly username?: string;
  readonly temp?: string;
  readonly desktop?: string;
  readonly lastLogon?: RDFDatetime;
  readonly fullName?: string;
  readonly userdomain?: string;
  readonly sid?: string;
  readonly userprofile?: string;
  readonly appdata?: string;
  readonly localappdata?: string;
  readonly internetCache?: string;
  readonly cookies?: string;
  readonly recent?: string;
  readonly personal?: string;
  readonly startup?: string;
  readonly localappdataLow?: string;
  readonly homedir?: string;
  readonly uid?: ProtoUint32;
  readonly gid?: ProtoUint32;
  readonly shell?: string;
  readonly pwEntry?: PwEntry;
  readonly gids?: readonly ProtoUint32[];
}

/** UserNotification.Type proto mapping. */
export enum UserNotificationType {
  TYPE_UNSET = 'TYPE_UNSET',
  TYPE_CLIENT_INTERROGATED = 'TYPE_CLIENT_INTERROGATED',
  TYPE_CLIENT_APPROVAL_REQUESTED = 'TYPE_CLIENT_APPROVAL_REQUESTED',
  TYPE_HUNT_APPROVAL_REQUESTED = 'TYPE_HUNT_APPROVAL_REQUESTED',
  TYPE_CRON_JOB_APPROVAL_REQUESTED = 'TYPE_CRON_JOB_APPROVAL_REQUESTED',
  TYPE_CLIENT_APPROVAL_GRANTED = 'TYPE_CLIENT_APPROVAL_GRANTED',
  TYPE_HUNT_APPROVAL_GRANTED = 'TYPE_HUNT_APPROVAL_GRANTED',
  TYPE_CRON_JOB_APPROVAL_GRANTED = 'TYPE_CRON_JOB_APPROVAL_GRANTED',
  TYPE_VFS_FILE_COLLECTED = 'TYPE_VFS_FILE_COLLECTED',
  TYPE_VFS_FILE_COLLECTION_FAILED = 'TYPE_VFS_FILE_COLLECTION_FAILED',
  TYPE_HUNT_STOPPED = 'TYPE_HUNT_STOPPED',
  TYPE_FILE_ARCHIVE_GENERATED = 'TYPE_FILE_ARCHIVE_GENERATED',
  TYPE_FILE_ARCHIVE_GENERATION_FAILED = 'TYPE_FILE_ARCHIVE_GENERATION_FAILED',
  TYPE_FLOW_RUN_COMPLETED = 'TYPE_FLOW_RUN_COMPLETED',
  TYPE_FLOW_RUN_FAILED = 'TYPE_FLOW_RUN_FAILED',
  TYPE_VFS_LIST_DIRECTORY_COMPLETED = 'TYPE_VFS_LIST_DIRECTORY_COMPLETED',
  TYPE_VFS_RECURSIVE_LIST_DIRECTORY_COMPLETED = 'TYPE_VFS_RECURSIVE_LIST_DIRECTORY_COMPLETED',
  TYPE_FILE_BLOB_FETCH_FAILED = 'TYPE_FILE_BLOB_FETCH_FAILED',
}

/** Volume proto mapping. */
export declare interface Volume {
  readonly isMounted?: boolean;
  readonly name?: string;
  readonly devicePath?: string;
  readonly fileSystemType?: string;
  readonly totalAllocationUnits?: ProtoUint64;
  readonly sectorsPerAllocationUnit?: ProtoUint64;
  readonly bytesPerSector?: ProtoUint64;
  readonly actualAvailableAllocationUnits?: ProtoUint64;
  readonly creationTime?: RDFDatetime;
  readonly fileSystemFlagList?: readonly VolumeVolumeFileSystemFlagEnum[];
  readonly serialNumber?: string;
  readonly windowsvolume?: WindowsVolume;
  readonly unixvolume?: UnixVolume;
}

/** Volume.VolumeFileSystemFlagEnum proto mapping. */
export enum VolumeVolumeFileSystemFlagEnum {
  FILE_CASE_SENSITIVE_SEARCH = 'FILE_CASE_SENSITIVE_SEARCH',
  FILE_CASE_PRESERVED_NAMES = 'FILE_CASE_PRESERVED_NAMES',
  FILE_UNICODE_ON_DISK = 'FILE_UNICODE_ON_DISK',
  FILE_PERSISTENT_ACLS = 'FILE_PERSISTENT_ACLS',
  FILE_FILE_COMPRESSION = 'FILE_FILE_COMPRESSION',
  FILE_VOLUME_QUOTAS = 'FILE_VOLUME_QUOTAS',
  FILE_SUPPORTS_SPARSE_FILES = 'FILE_SUPPORTS_SPARSE_FILES',
  FILE_SUPPORTS_REPARSE_POINTS = 'FILE_SUPPORTS_REPARSE_POINTS',
  FILE_SUPPORTS_REMOTE_STORAGE = 'FILE_SUPPORTS_REMOTE_STORAGE',
  FILE_VOLUME_IS_COMPRESSED = 'FILE_VOLUME_IS_COMPRESSED',
  FILE_SUPPORTS_OBJECT_IDS = 'FILE_SUPPORTS_OBJECT_IDS',
  FILE_SUPPORTS_ENCRYPTION = 'FILE_SUPPORTS_ENCRYPTION',
  FILE_NAMED_STREAMS = 'FILE_NAMED_STREAMS',
  FILE_READ_ONLY_VOLUME = 'FILE_READ_ONLY_VOLUME',
  FILE_SEQUENTIAL_WRITE_ONCE = 'FILE_SEQUENTIAL_WRITE_ONCE',
  FILE_SUPPORTS_TRANSACTIONS = 'FILE_SUPPORTS_TRANSACTIONS',
  FILE_SUPPORTS_HARD_LINKS = 'FILE_SUPPORTS_HARD_LINKS',
  FILE_SUPPORTS_EXTENDED_ATTRIBUTES = 'FILE_SUPPORTS_EXTENDED_ATTRIBUTES',
  FILE_SUPPORTS_OPEN_BY_FILE_ID = 'FILE_SUPPORTS_OPEN_BY_FILE_ID',
  FILE_SUPPORTS_USN_JOURNAL = 'FILE_SUPPORTS_USN_JOURNAL',
  FILE_SUPPORTS_INTEGRITY_STREAMS = 'FILE_SUPPORTS_INTEGRITY_STREAMS',
}

/** WindowsVolume proto mapping. */
export declare interface WindowsVolume {
  readonly attributesList?: readonly WindowsVolumeWindowsVolumeAttributeEnum[];
  readonly driveLetter?: string;
  readonly driveType?: WindowsVolumeWindowsDriveTypeEnum;
}

/** WindowsVolume.WindowsDriveTypeEnum proto mapping. */
export enum WindowsVolumeWindowsDriveTypeEnum {
  DRIVE_UNKNOWN = 'DRIVE_UNKNOWN',
  DRIVE_NO_ROOT_DIR = 'DRIVE_NO_ROOT_DIR',
  DRIVE_REMOVABLE = 'DRIVE_REMOVABLE',
  DRIVE_FIXED = 'DRIVE_FIXED',
  DRIVE_REMOTE = 'DRIVE_REMOTE',
  DRIVE_CDROM = 'DRIVE_CDROM',
  DRIVE_RAMDISK = 'DRIVE_RAMDISK',
}

/** WindowsVolume.WindowsVolumeAttributeEnum proto mapping. */
export enum WindowsVolumeWindowsVolumeAttributeEnum {
  READONLY = 'READONLY',
  HIDDEN = 'HIDDEN',
  NODEFAULTDRIVELETTER = 'NODEFAULTDRIVELETTER',
  SHADOWCOPY = 'SHADOWCOPY',
}

/** YaraMatch proto mapping. */
export declare interface YaraMatch {
  readonly ruleName?: string;
  readonly stringMatches?: readonly YaraStringMatch[];
}

/** YaraProcessDumpArgs proto mapping. */
export declare interface YaraProcessDumpArgs {
  readonly pids?: readonly ProtoUint64[];
  readonly processRegex?: string;
  readonly ignoreGrrProcess?: boolean;
  readonly dumpAllProcesses?: boolean;
  readonly sizeLimit?: ByteSize;
  readonly chunkSize?: ProtoUint64;
  readonly skipSpecialRegions?: boolean;
  readonly skipMappedFiles?: boolean;
  readonly skipSharedRegions?: boolean;
  readonly skipExecutableRegions?: boolean;
  readonly skipReadonlyRegions?: boolean;
  readonly prioritizeOffsets?: readonly ProtoUint64[];
  readonly ignoreParentProcesses?: boolean;
}

/** YaraProcessDumpInformation proto mapping. */
export declare interface YaraProcessDumpInformation {
  readonly process?: Process;
  readonly error?: string;
  readonly dumpTimeUs?: ProtoUint64;
  readonly memoryRegions?: readonly ProcessMemoryRegion[];
}

/** YaraProcessDumpResponse proto mapping. */
export declare interface YaraProcessDumpResponse {
  readonly dumpedProcesses?: readonly YaraProcessDumpInformation[];
  readonly errors?: readonly ProcessMemoryError[];
}

/** YaraProcessScanMatch proto mapping. */
export declare interface YaraProcessScanMatch {
  readonly process?: Process;
  readonly match?: readonly YaraMatch[];
  readonly scanTimeUs?: ProtoUint64;
}

/** YaraProcessScanMiss proto mapping. */
export declare interface YaraProcessScanMiss {
  readonly process?: Process;
  readonly scanTimeUs?: ProtoUint64;
}

/** YaraProcessScanRequest proto mapping. */
export declare interface YaraProcessScanRequest {
  readonly yaraSignature?: string;
  readonly yaraSignatureBlobId?: ProtoBytes;
  readonly signatureShard?: YaraSignatureShard;
  readonly numSignatureShards?: ProtoUint32;
  readonly pids?: readonly ProtoUint64[];
  readonly processRegex?: string;
  readonly cmdlineRegex?: string;
  readonly includeErrorsInResults?: YaraProcessScanRequestErrorPolicy;
  readonly includeMissesInResults?: boolean;
  readonly ignoreGrrProcess?: boolean;
  readonly ignoreParentProcesses?: boolean;
  readonly perProcessTimeout?: ProtoUint32;
  readonly chunkSize?: ProtoUint64;
  readonly overlapSize?: ProtoUint64;
  readonly skipSpecialRegions?: boolean;
  readonly skipMappedFiles?: boolean;
  readonly skipSharedRegions?: boolean;
  readonly skipExecutableRegions?: boolean;
  readonly skipReadonlyRegions?: boolean;
  readonly dumpProcessOnMatch?: boolean;
  readonly maxResultsPerProcess?: ProtoUint32;
  readonly processDumpSizeLimit?: ByteSize;
  readonly scanRuntimeLimitUs?: Duration;
  readonly contextWindow?: ProtoUint32;
  readonly implementationType?: YaraProcessScanRequestImplementationType;
}

/** YaraProcessScanRequest.ErrorPolicy proto mapping. */
export enum YaraProcessScanRequestErrorPolicy {
  NO_ERRORS = 'NO_ERRORS',
  ALL_ERRORS = 'ALL_ERRORS',
  CRITICAL_ERRORS = 'CRITICAL_ERRORS',
}

/** YaraProcessScanRequest.ImplementationType proto mapping. */
export enum YaraProcessScanRequestImplementationType {
  DEFAULT = 'DEFAULT',
  DIRECT = 'DIRECT',
  SANDBOX = 'SANDBOX',
}

/** YaraSignatureShard proto mapping. */
export declare interface YaraSignatureShard {
  readonly index?: ProtoUint32;
  readonly payload?: ProtoBytes;
}

/** YaraStringMatch proto mapping. */
export declare interface YaraStringMatch {
  readonly stringId?: string;
  readonly offset?: ProtoUint64;
  readonly data?: ProtoBytes;
  readonly context?: ProtoBytes;
}

/** protobuf2.TYPE_BOOL proto mapping. */
export type ProtoBool = boolean;

/** protobuf2.TYPE_BYTES proto mapping. */
export type ProtoBytes = string;

/** protobuf2.TYPE_DOUBLE proto mapping. */
export type ProtoDouble = number;

/** protobuf2.TYPE_FIXED32 proto mapping. */
export type ProtoFixed32 = number;

/** protobuf2.TYPE_FIXED64 proto mapping. */
export type ProtoFixed64 = string;

/** protobuf2.TYPE_FLOAT proto mapping. */
export type ProtoFloat = number;

/** protobuf2.TYPE_INT32 proto mapping. */
export type ProtoInt32 = number;

/** protobuf2.TYPE_INT64 proto mapping. */
export type ProtoInt64 = string;

/** protobuf2.TYPE_SFIXED32 proto mapping. */
export type ProtoSfixed32 = number;

/** protobuf2.TYPE_SFIXED64 proto mapping. */
export type ProtoSfixed64 = string;

/** protobuf2.TYPE_SINT32 proto mapping. */
export type ProtoSint32 = number;

/** protobuf2.TYPE_SINT64 proto mapping. */
export type ProtoSint64 = string;

/** protobuf2.TYPE_STRING proto mapping. */
export type ProtoString = string;

/** protobuf2.TYPE_UINT32 proto mapping. */
export type ProtoUint32 = number;

/** protobuf2.TYPE_UINT64 proto mapping. */
export type ProtoUint64 = string;

