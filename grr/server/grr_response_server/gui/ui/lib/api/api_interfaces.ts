/**
 * @fileoverview The module provides mappings for GRR API protos
 * (in JSON format) to TypeScript interfaces. This file is generated
 * from the OpenAPI description.
 */

// clang-format off

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

/** AmazonCloudInstance proto mapping. */
export declare interface AmazonCloudInstance {
  readonly instanceId?: string;
  readonly amiId?: string;
  readonly hostname?: string;
  readonly publicHostname?: string;
  readonly instanceType?: string;
}

/** AndExpression proto mapping. */
export declare interface AndExpression {
  readonly leftOperand?: SearchExpression;
  readonly rightOperand?: SearchExpression;
}

/** Anomaly proto mapping. */
export declare interface Anomaly {
  readonly type?: AnomalyAnomalyType;
  readonly severity?: AnomalyAnomalyLevel;
  readonly confidence?: AnomalyAnomalyLevel;
  readonly symptom?: string;
  readonly explanation?: string;
  readonly generatedBy?: string;
  readonly referencePathspec?: PathSpec;
  readonly anomalyReferenceId?: readonly string[];
  readonly finding?: readonly string[];
}

/** Anomaly.AnomalyLevel proto mapping. */
export enum AnomalyAnomalyLevel {
  UNKNOWN_ANOMALY_LEVEL = 'UNKNOWN_ANOMALY_LEVEL',
  VERY_LOW = 'VERY_LOW',
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  VERY_HIGH = 'VERY_HIGH',
}

/** Anomaly.AnomalyType proto mapping. */
export enum AnomalyAnomalyType {
  UNKNOWN_ANOMALY_TYPE = 'UNKNOWN_ANOMALY_TYPE',
  PARSER_ANOMALY = 'PARSER_ANOMALY',
  ANALYSIS_ANOMALY = 'ANALYSIS_ANOMALY',
  MANUAL_ANOMALY = 'MANUAL_ANOMALY',
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

/** ApiAuditChartReportData proto mapping. */
export declare interface ApiAuditChartReportData {
  readonly usedFields?: readonly string[];
  readonly rows?: readonly AuditEvent[];
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
  readonly path?: string;
  readonly children?: readonly ApiFile[];
}

/** ApiBrowseFilesystemResult proto mapping. */
export declare interface ApiBrowseFilesystemResult {
  readonly items?: readonly ApiBrowseFilesystemEntry[];
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
  readonly fleetspeakEnabled?: boolean;
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
  readonly users?: readonly User[];
  readonly volumes?: readonly Volume[];
  readonly age?: RDFDatetime;
  readonly cloudInstance?: CloudInstance;
  readonly sourceFlowId?: string;
}

/** ApiClientActionRequest proto mapping. */
export declare interface ApiClientActionRequest {
  readonly taskId?: ProtoUint64;
  readonly leasedUntil?: RDFDatetime;
  readonly sessionId?: RDFURN;
  readonly clientAction?: string;
  readonly responses?: readonly GrrMessage[];
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

/** ApiCreateClientApprovalArgs proto mapping. */
export declare interface ApiCreateClientApprovalArgs {
  readonly clientId?: string;
  readonly approval?: ApiClientApproval;
  readonly keepClientAlive?: boolean;
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

/** ApiCreatePerClientFileCollectionHuntArgs proto mapping. */
export declare interface ApiCreatePerClientFileCollectionHuntArgs {
  readonly description?: string;
  readonly durationSecs?: DurationSeconds;
  readonly perClientArgs?: readonly PerClientFileCollectionArgs[];
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
  readonly payloadType?: string;
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

/** ApiGetClientLoadStatsArgs proto mapping. */
export declare interface ApiGetClientLoadStatsArgs {
  readonly clientId?: string;
  readonly start?: RDFDatetime;
  readonly end?: RDFDatetime;
  readonly metric?: ApiGetClientLoadStatsArgsMetric;
}

/** ApiGetClientLoadStatsArgs.Metric proto mapping. */
export enum ApiGetClientLoadStatsArgsMetric {
  CPU_PERCENT = 'CPU_PERCENT',
  CPU_SYSTEM = 'CPU_SYSTEM',
  CPU_USER = 'CPU_USER',
  IO_READ_BYTES = 'IO_READ_BYTES',
  IO_WRITE_BYTES = 'IO_WRITE_BYTES',
  IO_READ_OPS = 'IO_READ_OPS',
  IO_WRITE_OPS = 'IO_WRITE_OPS',
  NETWORK_BYTES_RECEIVED = 'NETWORK_BYTES_RECEIVED',
  NETWORK_BYTES_SENT = 'NETWORK_BYTES_SENT',
  MEMORY_PERCENT = 'MEMORY_PERCENT',
  MEMORY_RSS_SIZE = 'MEMORY_RSS_SIZE',
  MEMORY_VMS_SIZE = 'MEMORY_VMS_SIZE',
}

/** ApiGetClientLoadStatsResult proto mapping. */
export declare interface ApiGetClientLoadStatsResult {
  readonly dataPoints?: readonly ApiStatsStoreMetricDataPoint[];
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

/** ApiGetDecodedFileArgs proto mapping. */
export declare interface ApiGetDecodedFileArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly decoderName?: string;
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

/** ApiGetFileDecodersArgs proto mapping. */
export declare interface ApiGetFileDecodersArgs {
  readonly clientId?: string;
  readonly filePath?: string;
}

/** ApiGetFileDecodersResult proto mapping. */
export declare interface ApiGetFileDecodersResult {
  readonly decoderNames?: readonly string[];
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

/** ApiGetFleetspeakPendingMessagesArgs proto mapping. */
export declare interface ApiGetFleetspeakPendingMessagesArgs {
  readonly clientId?: string;
  readonly offset?: ProtoUint64;
  readonly limit?: ProtoUint64;
  readonly wantData?: boolean;
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

/** ApiGetInterrogateOperationStateArgs proto mapping. */
export declare interface ApiGetInterrogateOperationStateArgs {
  readonly operationId?: string;
  readonly clientId?: string;
}

/** ApiGetInterrogateOperationStateResult proto mapping. */
export declare interface ApiGetInterrogateOperationStateResult {
  readonly state?: ApiGetInterrogateOperationStateResultState;
}

/** ApiGetInterrogateOperationStateResult.State proto mapping. */
export enum ApiGetInterrogateOperationStateResultState {
  RUNNING = 'RUNNING',
  FINISHED = 'FINISHED',
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

/** ApiGetRDFValueDescriptorArgs proto mapping. */
export declare interface ApiGetRDFValueDescriptorArgs {
  readonly type?: string;
}

/** ApiGetReportArgs proto mapping. */
export declare interface ApiGetReportArgs {
  readonly name?: string;
  readonly startTime?: RDFDatetime;
  readonly duration?: DurationSeconds;
  readonly clientLabel?: string;
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
  readonly interfaceTraits?: ApiGrrUserInterfaceTraits;
  readonly userType?: ApiGrrUserUserType;
  readonly email?: string;
}

/** ApiGrrUser.UserType proto mapping. */
export enum ApiGrrUserUserType {
  USER_TYPE_NONE = 'USER_TYPE_NONE',
  USER_TYPE_STANDARD = 'USER_TYPE_STANDARD',
  USER_TYPE_ADMIN = 'USER_TYPE_ADMIN',
}

/** ApiGrrUserInterfaceTraits proto mapping. */
export declare interface ApiGrrUserInterfaceTraits {
  readonly cronJobsNavItemEnabled?: boolean;
  readonly createCronJobActionEnabled?: boolean;
  readonly huntManagerNavItemEnabled?: boolean;
  readonly createHuntActionEnabled?: boolean;
  readonly showStatisticsNavItemEnabled?: boolean;
  readonly serverLoadNavItemEnabled?: boolean;
  readonly manageBinariesNavItemEnabled?: boolean;
  readonly uploadBinaryActionEnabled?: boolean;
  readonly settingsNavItemEnabled?: boolean;
  readonly artifactManagerNavItemEnabled?: boolean;
  readonly uploadArtifactActionEnabled?: boolean;
  readonly searchClientsActionEnabled?: boolean;
  readonly browseVirtualFileSystemNavItemEnabled?: boolean;
  readonly startClientFlowNavItemEnabled?: boolean;
  readonly manageClientFlowsNavItemEnabled?: boolean;
  readonly modifyClientLabelsActionEnabled?: boolean;
  readonly huntApprovalRequired?: boolean;
}

/** ApiHunt proto mapping. */
export declare interface ApiHunt {
  readonly urn?: SessionID;
  readonly huntId?: string;
  readonly huntType?: ApiHuntHuntType;
  readonly name?: string;
  readonly state?: ApiHuntState;
  readonly flowName?: string;
  readonly flowArgs?: Any;
  readonly huntRunnerArgs?: HuntRunnerArgs;
  readonly allClientsCount?: ProtoInt64;
  readonly remainingClientsCount?: ProtoInt64;
  readonly completedClientsCount?: ProtoInt64;
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
  readonly payloadType?: string;
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

/** ApiLineChartReportData proto mapping. */
export declare interface ApiLineChartReportData {
  readonly data?: readonly ApiReportDataSeries2D[];
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

/** ApiListClientActionRequestsArgs proto mapping. */
export declare interface ApiListClientActionRequestsArgs {
  readonly clientId?: string;
  readonly fetchResponses?: boolean;
}

/** ApiListClientActionRequestsResult proto mapping. */
export declare interface ApiListClientActionRequestsResult {
  readonly items?: readonly ApiClientActionRequest[];
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

/** ApiListFlowApplicableParsersArgs proto mapping. */
export declare interface ApiListFlowApplicableParsersArgs {
  readonly clientId?: string;
  readonly flowId?: string;
}

/** ApiListFlowApplicableParsersResult proto mapping. */
export declare interface ApiListFlowApplicableParsersResult {
  readonly parsers?: readonly ApiParserDescriptor[];
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

/** ApiListGrrBinariesResult proto mapping. */
export declare interface ApiListGrrBinariesResult {
  readonly items?: readonly ApiGrrBinary[];
}

/** ApiListHuntApprovalsArgs proto mapping. */
export declare interface ApiListHuntApprovalsArgs {
  readonly offset?: ProtoInt64;
  readonly count?: ProtoInt64;
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

/** ApiListKnownEncodingsResult proto mapping. */
export declare interface ApiListKnownEncodingsResult {
  readonly encodings?: readonly string[];
}

/** ApiListOutputPluginDescriptorsResult proto mapping. */
export declare interface ApiListOutputPluginDescriptorsResult {
  readonly items?: readonly ApiOutputPluginDescriptor[];
}

/** ApiListParsedFlowResultsArgs proto mapping. */
export declare interface ApiListParsedFlowResultsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly offset?: ProtoUint64;
  readonly count?: ProtoUint64;
}

/** ApiListParsedFlowResultsResult proto mapping. */
export declare interface ApiListParsedFlowResultsResult {
  readonly items?: readonly ApiFlowResult[];
  readonly errors?: readonly string[];
}

/** ApiListPendingUserNotificationsArgs proto mapping. */
export declare interface ApiListPendingUserNotificationsArgs {
  readonly timestamp?: RDFDatetime;
}

/** ApiListPendingUserNotificationsResult proto mapping. */
export declare interface ApiListPendingUserNotificationsResult {
  readonly items?: readonly ApiNotification[];
}

/** ApiListRDFValueDescriptorsResult proto mapping. */
export declare interface ApiListRDFValueDescriptorsResult {
  readonly items?: readonly ApiRDFValueDescriptor[];
}

/** ApiListReportsResult proto mapping. */
export declare interface ApiListReportsResult {
  readonly reports?: readonly ApiReport[];
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

/** ApiMethod proto mapping. */
export declare interface ApiMethod {
  readonly name?: string;
  readonly category?: string;
  readonly doc?: string;
  readonly httpRoute?: string;
  readonly httpMethods?: readonly string[];
  readonly argsTypeDescriptor?: ApiRDFValueDescriptor;
  readonly resultKind?: ApiMethodResultKind;
  readonly resultTypeDescriptor?: ApiRDFValueDescriptor;
}

/** ApiMethod.ResultKind proto mapping. */
export enum ApiMethodResultKind {
  NONE = 'NONE',
  VALUE = 'VALUE',
  BINARY_STREAM = 'BINARY_STREAM',
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

/** ApiParserDescriptor proto mapping. */
export declare interface ApiParserDescriptor {
  readonly name?: string;
  readonly type?: ApiParserDescriptorType;
}

/** ApiParserDescriptor.Type proto mapping. */
export enum ApiParserDescriptorType {
  UNKNOWN = 'UNKNOWN',
  SINGLE_RESPONSE = 'SINGLE_RESPONSE',
  MULTI_RESPONSE = 'MULTI_RESPONSE',
  SINGLE_FILE = 'SINGLE_FILE',
  MULTI_FILE = 'MULTI_FILE',
}

/** ApiPieChartReportData proto mapping. */
export declare interface ApiPieChartReportData {
  readonly data?: readonly ApiReportDataPoint1D[];
}

/** ApiRDFAllowedEnumValueDescriptor proto mapping. */
export declare interface ApiRDFAllowedEnumValueDescriptor {
  readonly name?: string;
  readonly value?: ProtoInt64;
  readonly doc?: string;
  readonly labels?: readonly string[];
}

/** ApiRDFValueDescriptor proto mapping. */
export declare interface ApiRDFValueDescriptor {
  readonly name?: string;
  readonly doc?: string;
  readonly kind?: ApiRDFValueDescriptorKind;
  readonly default?: Any;
  readonly parents?: readonly string[];
  readonly fields?: readonly ApiRDFValueFieldDescriptor[];
  readonly unionFieldName?: string;
}

/** ApiRDFValueDescriptor.Kind proto mapping. */
export enum ApiRDFValueDescriptorKind {
  PRIMITIVE = 'PRIMITIVE',
  STRUCT = 'STRUCT',
}

/** ApiRDFValueFieldDescriptor proto mapping. */
export declare interface ApiRDFValueFieldDescriptor {
  readonly name?: string;
  readonly type?: string;
  readonly index?: ProtoUint32;
  readonly repeated?: boolean;
  readonly dynamic?: boolean;
  readonly doc?: string;
  readonly friendlyName?: string;
  readonly contextHelpUrl?: string;
  readonly default?: Any;
  readonly labels?: readonly string[];
  readonly allowedValues?: readonly ApiRDFAllowedEnumValueDescriptor[];
}

/** ApiRemoveClientsLabelsArgs proto mapping. */
export declare interface ApiRemoveClientsLabelsArgs {
  readonly clientIds?: readonly string[];
  readonly labels?: readonly string[];
}

/** ApiReport proto mapping. */
export declare interface ApiReport {
  readonly desc?: ApiReportDescriptor;
  readonly data?: ApiReportData;
}

/** ApiReportData proto mapping. */
export declare interface ApiReportData {
  readonly representationType?: ApiReportDataRepresentationType;
  readonly stackChart?: ApiStackChartReportData;
  readonly pieChart?: ApiPieChartReportData;
  readonly lineChart?: ApiLineChartReportData;
  readonly auditChart?: ApiAuditChartReportData;
}

/** ApiReportData.RepresentationType proto mapping. */
export enum ApiReportDataRepresentationType {
  STACK_CHART = 'STACK_CHART',
  PIE_CHART = 'PIE_CHART',
  LINE_CHART = 'LINE_CHART',
  AUDIT_CHART = 'AUDIT_CHART',
}

/** ApiReportDataPoint1D proto mapping. */
export declare interface ApiReportDataPoint1D {
  readonly x?: ProtoFloat;
  readonly label?: string;
}

/** ApiReportDataPoint2D proto mapping. */
export declare interface ApiReportDataPoint2D {
  readonly x?: ProtoFloat;
  readonly y?: ProtoFloat;
}

/** ApiReportDataSeries2D proto mapping. */
export declare interface ApiReportDataSeries2D {
  readonly label?: string;
  readonly points?: readonly ApiReportDataPoint2D[];
}

/** ApiReportDescriptor proto mapping. */
export declare interface ApiReportDescriptor {
  readonly type?: ApiReportDescriptorReportType;
  readonly name?: string;
  readonly title?: string;
  readonly summary?: string;
  readonly requiresTimeRange?: boolean;
}

/** ApiReportDescriptor.ReportType proto mapping. */
export enum ApiReportDescriptorReportType {
  CLIENT = 'CLIENT',
  FILE_STORE = 'FILE_STORE',
  SERVER = 'SERVER',
}

/** ApiReportTickSpecifier proto mapping. */
export declare interface ApiReportTickSpecifier {
  readonly x?: ProtoFloat;
  readonly label?: string;
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

/** ApiStackChartReportData proto mapping. */
export declare interface ApiStackChartReportData {
  readonly data?: readonly ApiReportDataSeries2D[];
  readonly xTicks?: readonly ApiReportTickSpecifier[];
  readonly yTicks?: readonly ApiReportTickSpecifier[];
  readonly barWidth?: ProtoFloat;
}

/** ApiStatsStoreMetricDataPoint proto mapping. */
export declare interface ApiStatsStoreMetricDataPoint {
  readonly timestamp?: RDFDatetime;
  readonly value?: ProtoDouble;
}

/** ApiStructuredSearchClientsArgs proto mapping. */
export declare interface ApiStructuredSearchClientsArgs {
  readonly expression?: SearchExpression;
  readonly sortOrder?: SortOrder;
  readonly continuationToken?: ProtoBytes;
  readonly numberOfResults?: ProtoUint64;
}

/** ApiStructuredSearchClientsResult proto mapping. */
export declare interface ApiStructuredSearchClientsResult {
  readonly items?: readonly ApiClient[];
  readonly continuationToken?: ProtoBytes;
  readonly estimatedCount?: ProtoUint64;
}

/** ApiTimelineBodyOpts proto mapping. */
export declare interface ApiTimelineBodyOpts {
  readonly timestampSubsecondPrecision?: boolean;
  readonly inodeNtfsFileReferenceFormat?: boolean;
  readonly backslashEscape?: boolean;
  readonly carriageReturnEscape?: boolean;
  readonly nonPrintableEscape?: boolean;
}

/** ApiUiConfig proto mapping. */
export declare interface ApiUiConfig {
  readonly heading?: string;
  readonly reportUrl?: string;
  readonly helpUrl?: string;
  readonly grrVersion?: string;
  readonly profileImageUrl?: string;
  readonly defaultHuntRunnerArgs?: HuntRunnerArgs;
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
  readonly provides?: readonly string[];
  readonly sources?: readonly ArtifactSource[];
  readonly errorMessage?: string;
  readonly aliases?: readonly string[];
}

/** ArtifactCollectorFlowArgs proto mapping. */
export declare interface ArtifactCollectorFlowArgs {
  readonly artifactList?: readonly string[];
  readonly useTsk?: boolean;
  readonly useRawFilesystemAccess?: boolean;
  readonly splitOutputByArtifact?: boolean;
  readonly knowledgeBase?: KnowledgeBase;
  readonly errorOnNoResults?: boolean;
  readonly applyParsers?: boolean;
  readonly maxFileSize?: ByteSize;
  readonly dependencies?: ArtifactCollectorFlowArgsDependency;
  readonly ignoreInterpolationErrors?: boolean;
  readonly oldClientSnapshotFallback?: boolean;
  readonly recollectKnowledgeBase?: boolean;
  readonly implementationType?: PathSpecImplementationType;
}

/** ArtifactCollectorFlowArgs.Dependency proto mapping. */
export enum ArtifactCollectorFlowArgsDependency {
  USE_CACHED = 'USE_CACHED',
  IGNORE_DEPS = 'IGNORE_DEPS',
  FETCH_NOW = 'FETCH_NOW',
}

/** ArtifactCollectorFlowProgress proto mapping. */
export declare interface ArtifactCollectorFlowProgress {
  readonly artifacts?: readonly ArtifactProgress[];
}

/** ArtifactDescriptor proto mapping. */
export declare interface ArtifactDescriptor {
  readonly artifact?: Artifact;
  readonly dependencies?: readonly string[];
  readonly pathDependencies?: readonly string[];
  readonly processors?: readonly ArtifactProcessorDescriptor[];
  readonly isCustom?: boolean;
  readonly errorMessage?: string;
}

/** ArtifactFallbackCollectorArgs proto mapping. */
export declare interface ArtifactFallbackCollectorArgs {
  readonly artifactName?: string;
}

/** ArtifactFilesDownloaderFlowArgs proto mapping. */
export declare interface ArtifactFilesDownloaderFlowArgs {
  readonly artifactList?: readonly string[];
  readonly useTsk?: boolean;
  readonly useRawFilesystemAccess?: boolean;
  readonly maxFileSize?: ByteSize;
  readonly implementationType?: PathSpecImplementationType;
}

/** ArtifactFilesDownloaderResult proto mapping. */
export declare interface ArtifactFilesDownloaderResult {
  readonly originalResultType?: string;
  readonly originalResult?: ProtoBytes;
  readonly foundPathspec?: PathSpec;
  readonly downloadedFile?: StatEntry;
}

/** ArtifactProcessorDescriptor proto mapping. */
export declare interface ArtifactProcessorDescriptor {
  readonly name?: string;
  readonly description?: string;
  readonly outputTypes?: readonly string[];
}

/** ArtifactProgress proto mapping. */
export declare interface ArtifactProgress {
  readonly name?: string;
  readonly numResults?: ProtoUint32;
}

/** ArtifactSource proto mapping. */
export declare interface ArtifactSource {
  readonly type?: ArtifactSourceSourceType;
  readonly attributes?: Dict;
  readonly conditions?: readonly string[];
  readonly returnedTypes?: readonly string[];
  readonly supportedOs?: readonly string[];
}

/** ArtifactSource.SourceType proto mapping. */
export enum ArtifactSourceSourceType {
  COLLECTOR_TYPE_UNKNOWN = 'COLLECTOR_TYPE_UNKNOWN',
  FILE = 'FILE',
  REGISTRY_KEY = 'REGISTRY_KEY',
  REGISTRY_VALUE = 'REGISTRY_VALUE',
  WMI = 'WMI',
  ARTIFACT = 'ARTIFACT',
  PATH = 'PATH',
  DIRECTORY = 'DIRECTORY',
  ARTIFACT_GROUP = 'ARTIFACT_GROUP',
  GRR_CLIENT_ACTION = 'GRR_CLIENT_ACTION',
  LIST_FILES = 'LIST_FILES',
  ARTIFACT_FILES = 'ARTIFACT_FILES',
  GREP = 'GREP',
  COMMAND = 'COMMAND',
  REKALL_PLUGIN = 'REKALL_PLUGIN',
}

/** AttributedDict proto mapping. */
export declare interface AttributedDict {
  readonly dat?: readonly KeyValue[];
}

/** AuditEvent proto mapping. */
export declare interface AuditEvent {
  readonly id?: ProtoInt32;
  readonly user?: string;
  readonly action?: AuditEventAction;
  readonly flowName?: string;
  readonly flowArgs?: ProtoBytes;
  readonly client?: RDFURN;
  readonly timestamp?: RDFDatetime;
  readonly description?: string;
  readonly urn?: RDFURN;
}

/** AuditEvent.Action proto mapping. */
export enum AuditEventAction {
  UNKNOWN = 'UNKNOWN',
  RUN_FLOW = 'RUN_FLOW',
  CLIENT_APPROVAL_BREAK_GLASS_REQUEST = 'CLIENT_APPROVAL_BREAK_GLASS_REQUEST',
  CLIENT_APPROVAL_GRANT = 'CLIENT_APPROVAL_GRANT',
  CLIENT_APPROVAL_REQUEST = 'CLIENT_APPROVAL_REQUEST',
  CRON_APPROVAL_GRANT = 'CRON_APPROVAL_GRANT',
  CRON_APPROVAL_REQUEST = 'CRON_APPROVAL_REQUEST',
  HUNT_APPROVAL_GRANT = 'HUNT_APPROVAL_GRANT',
  HUNT_APPROVAL_REQUEST = 'HUNT_APPROVAL_REQUEST',
  HUNT_CREATED = 'HUNT_CREATED',
  HUNT_MODIFIED = 'HUNT_MODIFIED',
  HUNT_PAUSED = 'HUNT_PAUSED',
  HUNT_STARTED = 'HUNT_STARTED',
  HUNT_STOPPED = 'HUNT_STOPPED',
  CLIENT_ADD_LABEL = 'CLIENT_ADD_LABEL',
  CLIENT_REMOVE_LABEL = 'CLIENT_REMOVE_LABEL',
  USER_ADD = 'USER_ADD',
  USER_UPDATE = 'USER_UPDATE',
  USER_DELETE = 'USER_DELETE',
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
  CHROME = 'CHROME',
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

/** CAEnrolerArgs proto mapping. */
export declare interface CAEnrolerArgs {
  readonly csr?: Certificate;
}

/** CacheGrepArgs proto mapping. */
export declare interface CacheGrepArgs {
  readonly grepUsers?: readonly string[];
  readonly pathtype?: PathSpecPathType;
  readonly dataRegex?: ProtoBytes;
  readonly checkChrome?: boolean;
  readonly checkFirefox?: boolean;
  readonly checkIe?: boolean;
}

/** Certificate proto mapping. */
export declare interface Certificate {
  readonly type?: CertificateType;
  readonly pem?: ProtoBytes;
  readonly cn?: string;
}

/** Certificate.Type proto mapping. */
export enum CertificateType {
  CSR = 'CSR',
  CRT = 'CRT',
  CA = 'CA',
}

/** CheckFlowArgs proto mapping. */
export declare interface CheckFlowArgs {
  readonly onlyOs?: readonly string[];
  readonly onlyCpe?: readonly string[];
  readonly onlyLabel?: readonly string[];
  readonly maxFindings?: readonly ProtoUint64[];
  readonly restrictChecks?: readonly string[];
}

/** CheckResult proto mapping. */
export declare interface CheckResult {
  readonly checkId?: string;
  readonly anomaly?: readonly Anomaly[];
}

/** ChromeHistoryArgs proto mapping. */
export declare interface ChromeHistoryArgs {
  readonly pathtype?: PathSpecPathType;
  readonly getArchive?: boolean;
  readonly username?: string;
  readonly historyPath?: string;
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
  readonly nannyStatus?: string;
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

/** ClientStats proto mapping. */
export declare interface ClientStats {
  readonly cpuSamples?: readonly CpuSample[];
  readonly rssSize?: ProtoUint64;
  readonly vmsSize?: ProtoUint64;
  readonly memoryPercent?: ProtoFloat;
  readonly bytesReceived?: ProtoUint64;
  readonly bytesSent?: ProtoUint64;
  readonly ioSamples?: readonly IOSample[];
  readonly createTime?: RDFDatetime;
  readonly bootTime?: RDFDatetime;
  readonly timestamp?: RDFDatetime;
}

/** ClientSummary proto mapping. */
export declare interface ClientSummary {
  readonly clientId?: string;
  readonly timestamp?: RDFDatetime;
  readonly systemInfo?: Uname;
  readonly clientInfo?: ClientInformation;
  readonly installDate?: RDFDatetime;
  readonly interfaces?: readonly Interface[];
  readonly serialNumber?: string;
  readonly systemManufacturer?: string;
  readonly systemUuid?: string;
  readonly users?: readonly User[];
  readonly cloudType?: CloudInstanceInstanceType;
  readonly cloudInstanceId?: string;
  readonly lastPing?: RDFDatetime;
  readonly edrAgents?: readonly EdrAgent[];
  readonly fleetspeakValidationInfo?: FleetspeakValidationInfo;
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

/** CollectSingleFileArgs proto mapping. */
export declare interface CollectSingleFileArgs {
  readonly path?: string;
  readonly maxSizeBytes?: ByteSize;
}

/** CollectSingleFileProgress proto mapping. */
export declare interface CollectSingleFileProgress {
  readonly status?: CollectSingleFileProgressStatus;
  readonly result?: CollectSingleFileResult;
  readonly errorDescription?: string;
}

/** CollectSingleFileProgress.Status proto mapping. */
export enum CollectSingleFileProgressStatus {
  UNDEFINED = 'UNDEFINED',
  IN_PROGRESS = 'IN_PROGRESS',
  COLLECTED = 'COLLECTED',
  NOT_FOUND = 'NOT_FOUND',
  FAILED = 'FAILED',
}

/** CollectSingleFileResult proto mapping. */
export declare interface CollectSingleFileResult {
  readonly stat?: StatEntry;
  readonly hash?: Hash;
}

/** ConditionExpression proto mapping. */
export declare interface ConditionExpression {
  readonly conditionType?: ConditionExpressionConditionType;
  readonly osCondition?: OSCondition;
}

/** ConditionExpression.ConditionType proto mapping. */
export enum ConditionExpressionConditionType {
  UNKNOWN = 'UNKNOWN',
  OS = 'OS',
}

/** CpuSample proto mapping. */
export declare interface CpuSample {
  readonly userCpuTime?: ProtoFloat;
  readonly systemCpuTime?: ProtoFloat;
  readonly cpuPercent?: ProtoFloat;
  readonly timestamp?: RDFDatetime;
}

/** CpuSeconds proto mapping. */
export declare interface CpuSeconds {
  readonly userCpuTime?: ProtoFloat;
  readonly systemCpuTime?: ProtoFloat;
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

/** DeleteGRRTempFilesArgs proto mapping. */
export declare interface DeleteGRRTempFilesArgs {
  readonly pathspec?: PathSpec;
}

/** Dict proto mapping. */
export declare interface Dict {
  readonly dat?: readonly KeyValue[];
}

/** DiskVolumeInfoArgs proto mapping. */
export declare interface DiskVolumeInfoArgs {
  readonly pathList?: readonly string[];
  readonly pathtype?: PathSpecPathType;
}

/** DumpACPITableArgs proto mapping. */
export declare interface DumpACPITableArgs {
  readonly logging?: boolean;
  readonly tableSignatureList?: readonly string[];
}

/** DumpEfiImageResponse proto mapping. */
export declare interface DumpEfiImageResponse {
  readonly eficheckVersion?: string;
  readonly path?: PathSpec;
  readonly response?: ExecuteBinaryResponse;
}

/** DumpFlashImageArgs proto mapping. */
export declare interface DumpFlashImageArgs {
  readonly logLevel?: ProtoUint32;
  readonly chunkSize?: ProtoUint32;
  readonly notifySyslog?: boolean;
}

/** EdrAgent proto mapping. */
export declare interface EdrAgent {
  readonly name?: string;
  readonly agentId?: string;
  readonly backendId?: string;
}

/** EfiCollection proto mapping. */
export declare interface EfiCollection {
  readonly eficheckVersion?: string;
  readonly bootRomVersion?: string;
  readonly entries?: readonly EfiEntry[];
}

/** EfiEntry proto mapping. */
export declare interface EfiEntry {
  readonly volumeType?: ProtoUint32;
  readonly address?: ProtoUint64;
  readonly size?: ProtoUint32;
  readonly guid?: string;
  readonly hash?: string;
  readonly flags?: ProtoUint32;
  readonly index?: ProtoUint32;
}

/** EficheckFlowArgs proto mapping. */
export declare interface EficheckFlowArgs {
  readonly cmdPath?: string;
}

/** EmbeddedRDFValue proto mapping. */
export declare interface EmbeddedRDFValue {
  readonly embeddedAge?: RDFDatetime;
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

/** ExecuteCommandArgs proto mapping. */
export declare interface ExecuteCommandArgs {
  readonly cmd?: string;
  readonly commandLine?: string;
  readonly timeLimit?: ProtoInt64;
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

/** FindFilesArgs proto mapping. */
export declare interface FindFilesArgs {
  readonly findspec?: FindSpec;
}

/** FindSpec proto mapping. */
export declare interface FindSpec {
  readonly iterator?: Iterator;
  readonly pathspec?: PathSpec;
  readonly pathGlob?: GlobExpression;
  readonly pathRegex?: string;
  readonly dataRegex?: RDFBytes;
  readonly startTime?: RDFDatetime;
  readonly endTime?: RDFDatetime;
  readonly crossDevs?: boolean;
  readonly maxDepth?: ProtoInt32;
  readonly hit?: StatEntry;
  readonly maxData?: ProtoUint64;
  readonly minFileSize?: ProtoUint64;
  readonly maxFileSize?: ProtoUint64;
  readonly permMask?: ProtoUint64;
  readonly permMode?: ProtoUint64;
  readonly uid?: ProtoUint64;
  readonly gid?: ProtoUint64;
  readonly collectExtAttrs?: boolean;
}

/** FingerprintFileArgs proto mapping. */
export declare interface FingerprintFileArgs {
  readonly pathspec?: PathSpec;
}

/** FirefoxHistoryArgs proto mapping. */
export declare interface FirefoxHistoryArgs {
  readonly pathtype?: PathSpecPathType;
  readonly getArchive?: boolean;
  readonly username?: string;
  readonly historyPath?: string;
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
  readonly notifyToUser?: boolean;
  readonly clientId?: string;
  readonly queue?: RDFURN;
  readonly cpuLimit?: ProtoUint64;
  readonly networkBytesLimit?: ProtoUint64;
  readonly requestState?: RequestState;
  readonly flowName?: string;
  readonly baseSessionId?: RDFURN;
  readonly logsCollectionUrn?: RDFURN;
  readonly writeIntermediateResults?: boolean;
  readonly requireFastpoll?: boolean;
  readonly outputPlugins?: readonly OutputPluginDescriptor[];
  readonly originalFlow?: FlowReference;
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
  CLIENT_CLOCK = 'CLIENT_CLOCK',
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
  UNAME = 'UNAME',
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

/** GetFileArgs proto mapping. */
export declare interface GetFileArgs {
  readonly pathspec?: PathSpec;
  readonly readLength?: ProtoUint64;
  readonly ignoreStatFailure?: boolean;
}

/** GetMBRArgs proto mapping. */
export declare interface GetMBRArgs {
  readonly length?: ProtoUint64;
}

/** GlobArgs proto mapping. */
export declare interface GlobArgs {
  readonly paths?: readonly GlobExpression[];
  readonly pathtype?: PathSpecPathType;
  readonly rootPath?: PathSpec;
  readonly processNonRegularFiles?: boolean;
  readonly implementationType?: PathSpecImplementationType;
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
  readonly args?: ProtoBytes;
  readonly arg?: EmbeddedRDFValue;
  readonly source?: RDFURN;
  readonly authState?: GrrMessageAuthorizationState;
  readonly type?: GrrMessageType;
  readonly ttl?: ProtoUint32;
  readonly requireFastpoll?: boolean;
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
  readonly nannyStatus?: string;
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
  readonly queue?: RDFURN;
  readonly cpuLimit?: ProtoUint64;
  readonly networkBytesLimit?: ProtoUint64;
  readonly clientLimit?: ProtoUint64;
  readonly crashLimit?: ProtoUint64;
  readonly avgResultsPerClientLimit?: ProtoUint64;
  readonly avgCpuSecondsPerClientLimit?: ProtoUint64;
  readonly avgNetworkBytesPerClientLimit?: ProtoUint64;
  readonly expiryTime?: DurationSeconds;
  readonly clientRate?: ProtoFloat;
  readonly addForemanRules?: boolean;
  readonly crashAlertEmail?: string;
  readonly outputPlugins?: readonly OutputPluginDescriptor[];
  readonly perClientCpuLimit?: ProtoUint64;
  readonly perClientNetworkLimitBytes?: ProtoUint64;
  readonly originalObject?: FlowLikeObjectReference;
}

/** IOSample proto mapping. */
export declare interface IOSample {
  readonly readCount?: ProtoUint64;
  readonly writeCount?: ProtoUint64;
  readonly readBytes?: ProtoUint64;
  readonly writeBytes?: ProtoUint64;
  readonly timestamp?: RDFDatetime;
}

/** Interface proto mapping. */
export declare interface Interface {
  readonly macAddress?: ProtoBytes;
  readonly ip4Addresses?: readonly ProtoBytes[];
  readonly ifname?: string;
  readonly ip6Addresses?: readonly ProtoBytes[];
  readonly addresses?: readonly NetworkAddress[];
  readonly dhcpLeaseExpires?: RDFDatetime;
  readonly dhcpLeaseObtained?: RDFDatetime;
  readonly dhcpServerList?: readonly NetworkAddress[];
  readonly ipGatewayList?: readonly NetworkAddress[];
}

/** InterrogateArgs proto mapping. */
export declare interface InterrogateArgs {
  readonly lightweight?: boolean;
}

/** Iterator proto mapping. */
export declare interface Iterator {
  readonly clientState?: Dict;
  readonly skip?: ProtoUint32;
  readonly number?: ProtoUint32;
  readonly state?: IteratorState;
}

/** Iterator.State proto mapping. */
export enum IteratorState {
  RUNNING = 'RUNNING',
  FINISHED = 'FINISHED',
}

/** KeepAliveArgs proto mapping. */
export declare interface KeepAliveArgs {
  readonly duration?: DurationSeconds;
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

/** LaunchBinaryArgs proto mapping. */
export declare interface LaunchBinaryArgs {
  readonly binary?: RDFURN;
  readonly commandLine?: string;
}

/** ListDirectoryArgs proto mapping. */
export declare interface ListDirectoryArgs {
  readonly pathspec?: PathSpec;
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
  INET6_WIN = 'INET6_WIN',
  INET6_OSX = 'INET6_OSX',
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

/** NotExpression proto mapping. */
export declare interface NotExpression {
  readonly expression?: SearchExpression;
}

/** OSCondition proto mapping. */
export declare interface OSCondition {
  readonly comparisonType?: OSConditionComparisonType;
  readonly os?: string;
}

/** OSCondition.ComparisonType proto mapping. */
export enum OSConditionComparisonType {
  UNKNOWN = 'UNKNOWN',
  EQUALS = 'EQUALS',
  NOT_EQUALS = 'NOT_EQUALS',
  CONTAINS = 'CONTAINS',
}

/** OnlineNotificationArgs proto mapping. */
export declare interface OnlineNotificationArgs {
  readonly email?: string;
}

/** OrExpression proto mapping. */
export declare interface OrExpression {
  readonly leftOperand?: SearchExpression;
  readonly rightOperand?: SearchExpression;
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
  readonly pluginArgs?: ProtoBytes;
  readonly args?: Any;
}

/** OutputPluginState proto mapping. */
export declare interface OutputPluginState {
  readonly pluginDescriptor?: OutputPluginDescriptor;
  readonly pluginState?: AttributedDict;
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

/** PerClientFileCollectionArgs proto mapping. */
export declare interface PerClientFileCollectionArgs {
  readonly clientId?: string;
  readonly pathType?: PathSpecPathType;
  readonly paths?: readonly string[];
}

/** PlistRequest proto mapping. */
export declare interface PlistRequest {
  readonly pathspec?: PathSpec;
  readonly context?: string;
  readonly query?: string;
}

/** PlistValueFilterArgs proto mapping. */
export declare interface PlistValueFilterArgs {
  readonly request?: PlistRequest;
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
  readonly cpuPercent?: ProtoFloat;
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

/** RecursiveListDirectoryArgs proto mapping. */
export declare interface RecursiveListDirectoryArgs {
  readonly pathspec?: PathSpec;
  readonly maxDepth?: ProtoUint64;
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

/** SearchExpression proto mapping. */
export declare interface SearchExpression {
  readonly expressionType?: SearchExpressionExpressionType;
  readonly notExpression?: NotExpression;
  readonly andExpression?: AndExpression;
  readonly orExpression?: OrExpression;
  readonly conditionExpression?: ConditionExpression;
}

/** SearchExpression.ExpressionType proto mapping. */
export enum SearchExpressionExpressionType {
  UNKNOWN = 'UNKNOWN',
  NEGATION = 'NEGATION',
  AND = 'AND',
  OR = 'OR',
  CONDITION = 'CONDITION',
}

/** SendFileRequest proto mapping. */
export declare interface SendFileRequest {
  readonly pathspec?: PathSpec;
  readonly addressFamily?: NetworkAddressFamily;
  readonly host?: string;
  readonly port?: ProtoUint64;
  readonly key?: ProtoBytes;
  readonly iv?: ProtoBytes;
}

/** SortOrder proto mapping. */
export declare interface SortOrder {
  readonly orderBy?: SortOrderOrderBy;
  readonly order?: SortOrderOrder;
}

/** SortOrder.Order proto mapping. */
export enum SortOrderOrder {
  UNKNOWN_ORDER = 'UNKNOWN_ORDER',
  ASCENDING = 'ASCENDING',
  DESCENDING = 'DESCENDING',
}

/** SortOrder.OrderBy proto mapping. */
export enum SortOrderOrderBy {
  UNKNOWN = 'UNKNOWN',
  SNAPSHOT_CREATION_TIME = 'SNAPSHOT_CREATION_TIME',
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

/** StatsHistogram proto mapping. */
export declare interface StatsHistogram {
  readonly bins?: readonly StatsHistogramBin[];
}

/** StatsHistogramBin proto mapping. */
export declare interface StatsHistogramBin {
  readonly rangeMaxValue?: ProtoFloat;
  readonly num?: ProtoUint64;
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

/** UninstallArgs proto mapping. */
export declare interface UninstallArgs {
  readonly kill?: boolean;
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

/** UpdateConfigurationArgs proto mapping. */
export declare interface UpdateConfigurationArgs {
  readonly config?: Dict;
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
}

/** YaraProcessDumpInformation proto mapping. */
export declare interface YaraProcessDumpInformation {
  readonly process?: Process;
  readonly dumpFiles?: readonly PathSpec[];
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

// clang-format on
