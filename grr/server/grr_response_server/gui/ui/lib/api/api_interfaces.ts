
/**
 * @fileoverview The module provides mappings for GRR API protos (in JSON
 * format) into TypeScript interfaces. They are not intended to be
 * complete: only actually used fields are mapped.
 *
 * TODO(user): Using Protobuf-code generation instead of manually writing
 * interface definitions is preferable, but it's a non-trivial task, since code
 * generation should be supported by OpenSource build pipeline.
 */

export declare interface AnyObject {
  '@type'?: string;
  [key: string]: undefined|null|string|number|boolean|object;
}

/**
 * int64, fixed64, and DecimalString in Protobuf are serialized as string in
 * JSON because JS loses precision for big numeric types. During
 * deserialization, both decimal strings and numbers are accepted.
 */
export type DecimalString = string|number|bigint;

/**
 * ApiUser protomapping.
 */
export declare interface ApiUser {
  readonly username?: string;
  readonly lastLogon?: string;
  readonly fullName?: string;
  readonly homedir?: string;
  readonly uid?: number;
  readonly gid?: number;
  readonly shell?: string;
}

/**
 * Network address proto mapping
 */
export declare interface ApiNetworkAddress {
  readonly addressType?: string;
  readonly packedBytes?: string;
}

/**
 * Network Interface proto mapping
 */
export declare interface ApiInterface {
  readonly macAddress?: string;
  readonly ifname?: string;
  readonly addresses?: ReadonlyArray<ApiNetworkAddress>;
}

/**
 * bytes are represented as base64-encoded strings.
 */
export type ByteString = string;

/**
 * KnowledgeBase proto mapping.
 */
export declare interface ApiKnowledgeBase {
  readonly fqdn?: string;
  readonly timeZone?: string;
  readonly os?: string;
  readonly osMajorVersion?: number;
  readonly osMinorVersion?: number;
}

/**
 * ApiClientInformation proto mapping.
 */
export declare interface ApiClientInformation {
  readonly clientName?: string;
  readonly clientVersion?: number;
  readonly revision?: DecimalString;
  readonly buildTime?: string;
  readonly clientBinaryName?: string;
  readonly clientDescription?: string;
  readonly labels?: ReadonlyArray<string>;
  readonly timelineBtimeSupport?: boolean;
  readonly sandboxSupport?: boolean;
  readonly hardwareInfo?: HardwareInfo;
}

/** ApiWindowsVolume proto mapping. */
export declare interface ApiWindowsVolume {
  readonly attributesList?: ReadonlyArray<string>;
  readonly driveLetter?: string;
  readonly driveType?: string;
}

/** ApiUnixVolume proto mapping. */
export declare interface ApiUnixVolume {
  readonly mountPoint?: string;
  readonly options?: string;
}

/** ApiVolume proto mapping. */
export declare interface ApiVolume {
  readonly name?: string;
  readonly devicePath?: string;
  readonly fileSystemType?: string;
  readonly totalAllocationUnits?: DecimalString;
  readonly sectorsPerAllocationUnit?: DecimalString;
  readonly bytesPerSector?: DecimalString;
  readonly actualAvailableAllocationUnits?: DecimalString;
  readonly creationTime?: string;
  readonly windowsvolume?: ApiWindowsVolume;
  readonly unixvolume?: ApiUnixVolume;
}

/**
 * ClientLabel proto mapping.
 */
export declare interface ApiClientLabel {
  readonly owner?: string;
  readonly name?: string;
}

/**
 * ApiUname proto mapping.
 */
export declare interface ApiUname {
  readonly system?: string;
  readonly node?: string;
  readonly release?: string;
  readonly version?: string;
  readonly machine?: string;
  readonly kernel?: string;
  readonly fqdn?: string;
  readonly installDate?: string;
  readonly libcVer?: string;
  readonly architecture?: string;
  readonly pep425tag?: string;
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

/** AmazonCloudInstance proto mapping. */
export declare interface AmazonCloudInstance {
  readonly instanceId?: string;
  readonly amiId?: string;
  readonly hostname?: string;
  readonly publicHostname?: string;
  readonly instanceType?: string;
}

/** CloudInstance.InstanceType proto mapping. */
export enum CloudInstanceInstanceType {
  UNSET = 'UNSET',
  AMAZON = 'AMAZON',
  GOOGLE = 'GOOGLE',
}

/** CloudInstance proto mapping. */
export declare interface CloudInstance {
  readonly cloudType?: CloudInstanceInstanceType;
  readonly google?: GoogleCloudInstance;
  readonly amazon?: AmazonCloudInstance;
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

/**
 * ApiListClientsLabelsResult proto mapping.
 */
export declare interface ApiListClientsLabelsResult {
  readonly items?: ReadonlyArray<ApiClientLabel>;
}

/**
 * AddClientsLabelsArgs proto mapping.
 */
export declare interface ApiAddClientsLabelsArgs {
  readonly clientIds: ReadonlyArray<string>;
  readonly labels: ReadonlyArray<string>;
}

/** ApiRemoveClientsLabelsArgs proto mapping. */
export declare interface ApiRemoveClientsLabelsArgs {
  readonly clientIds?: ReadonlyArray<string>;
  readonly labels?: ReadonlyArray<string>;
}

/**
 * ApiClient proto mapping.
 */
export declare interface ApiClient {
  readonly clientId?: string;
  readonly sourceFlowId?: string;
  readonly urn?: string;

  readonly fleetspeakEnabled?: boolean;

  readonly agentInfo?: ApiClientInformation;
  readonly knowledgeBase?: ApiKnowledgeBase;

  readonly osInfo?: ApiUname;
  readonly interfaces?: ReadonlyArray<ApiInterface>;
  readonly users?: ReadonlyArray<ApiUser>;
  readonly volumes?: ReadonlyArray<ApiVolume>;
  readonly memorySize?: DecimalString;
  readonly firstSeenAt?: string;
  readonly lastSeenAt?: string;
  readonly lastBootedAt?: string;
  readonly lastClock?: string;
  readonly labels?: ReadonlyArray<ApiClientLabel>;
  readonly age?: string;
  readonly cloudInstance?: CloudInstance;
  readonly hardwareInfo?: HardwareInfo;
}

/** ClientSummary proto mapping. */
export declare interface ClientSummary {
  readonly systemInfo?: ApiUname;
  readonly users?: ReadonlyArray<ApiUser>;
}

/**
 * ApiGetClientVersionsResult proto mapping.
 */
export declare interface ApiGetClientVersionsResult {
  readonly items?: ReadonlyArray<ApiClient>;
}

/**
 * ApiSearchClientsArgs proto mapping.
 */
export declare interface ApiSearchClientsArgs {
  readonly query?: string;
  readonly offset?: DecimalString;
  readonly count?: DecimalString;
}

/**
 * ApiSearchClientResult proto mapping.
 */
export declare interface ApiSearchClientResult {
  readonly items?: ReadonlyArray<ApiClient>;
}

/** /config/Email.approval_optional_cc_address proto mapping. */
export declare interface ApiApprovalOptionalCcAddressResult {
  readonly value?: {
    value?: string,
  };
}

/** ApiClientApproval proto mapping */
export declare interface ApiClientApproval {
  readonly subject?: ApiClient;
  readonly id?: string;
  readonly requestor?: string;
  readonly reason?: string;
  readonly isValid?: boolean;
  readonly isValidMessage?: string;
  readonly notifiedUsers?: string[];
  readonly approvers?: string[];
  readonly emailCcAddresses?: string[];
}

/** ApiListClientApprovalsResult proto mapping */
export declare interface ApiListClientApprovalsResult {
  readonly items?: ApiClientApproval[];
}

/** ApiFlowDescriptor proto mapping. */
export declare interface ApiFlowDescriptor {
  readonly name?: string;
  readonly friendlyName?: string;
  readonly category?: string;
  readonly defaultArgs?: AnyObject;
}

/** ApiListClientFlowDescriptorsResult proto mapping. */
export declare interface ApiListClientFlowDescriptorsResult {
  readonly items?: ReadonlyArray<ApiFlowDescriptor>;
}

/** ApiFlow.State proto enum mapping. */
export enum ApiFlowState {
  RUNNING = 'RUNNING',
  TERMINATED = 'TERMINATED',
  ERROR = 'ERROR',
  CLIENT_CRASHED = 'CLIENT_CRASHED',
}

/** ApiFlow proto mapping. */
export declare interface ApiFlow {
  readonly flowId?: string;
  readonly clientId?: string;
  readonly lastActiveAt?: string;
  readonly startedAt?: string;
  readonly name?: string;
  readonly creator?: string;
  readonly args?: AnyObject;
  readonly progress?: AnyObject;
  readonly state?: ApiFlowState;
  readonly errorDescription?: string;
  readonly resultMetadata?: FlowResultMetadata;
}

/** ApiListFlowsResult proto mapping. */
export declare interface ApiListFlowsResult {
  readonly items?: ReadonlyArray<ApiFlow>;
}

/** ApiCreateFlowArgs proto mapping. */
export declare interface ApiCreateFlowArgs {
  clientId: string;
  flow: {name: string; args: AnyObject;};
}

/** ApiCreateClientApprovalArgs proto mapping. */
export declare interface ApiCreateClientApprovalArgs {
  clientId?: string;
  approval?: ApiClientApproval;
}

/** ApiFlowResult proto mapping */
export declare interface ApiFlowResult {
  readonly payload?: AnyObject;
  readonly payloadType?: string;
  readonly timestamp?: string;
  readonly tag?: string;
}

/** ApiListFlowResultsArgs proto mapping. */
export declare interface ApiListFlowResultsArgs {
  readonly clientId?: string;
  readonly flowId?: string;
  readonly offset?: number;
  readonly count?: number;
  readonly withType?: string;
  readonly withTag?: string;
}

/** ApiListFlowResultsResult proto mapping. */
export declare interface ApiListFlowResultsResult {
  readonly items?: ReadonlyArray<ApiFlowResult>;
  readonly totalCount?: number;
}

/** GUISettings proto mapping. */
export declare interface GUISettings {
  mode?: GUISettingsUIMode;
  canaryMode?: boolean;
}

/** GUISettings namespaced (used for enum declarations). */
export enum GUISettingsUIMode {
  BASIC = 'BASIC',
  ADVANCED = 'ADVANCED',
  DEBUG = 'DEBUG',
}

/** ApiGrrUserInterfaceTraits proto mapping. */
export declare interface ApiGrrUserInterfaceTraits {
  cronJobsNavItemEnabled?: boolean;
  createCronJobActionEnabled?: boolean;

  huntManagerNavItemEnabled?: boolean;
  createHuntActionEnabled?: boolean;

  showStatisticsNavItemEnabled?: boolean;

  serverLoadNavItemEnabled?: boolean;

  manageBinariesNavItemEnabled?: boolean;
  uploadBinaryActionEnabled?: boolean;

  settingsNavItemEnabled?: boolean;

  artifactManagerNavItemEnabled?: boolean;
  uploadArtifactActionEnabled?: boolean;

  searchClientsActionEnabled?: boolean;
  browseVirtualFileSystemNavItemEnabled?: boolean;
  startClientFlowNavItemEnabled?: boolean;
  manageClientFlowsNavItemEnabled?: boolean;
  modifyClientLabelsActionEnabled?: boolean;

  huntApprovalRequired?: boolean;
}

/** ApiGrrUser proto mapping. */
export declare interface ApiGrrUser {
  username?: string;
  settings?: GUISettings;
  interfaceTraits?: ApiGrrUserInterfaceTraits;
  userType?: ApiGrrUserUserType;
  email?: string;
}

/** ApiGrrUser.UserType mapping. */
export enum ApiGrrUserUserType {
  USER_TYPE_NONE = 'USER_TYPE_NONE',
  USER_TYPE_STANDARD = 'USER_TYPE_STANDARD',
  USER_TYPE_ADMIN = 'USER_TYPE_ADMIN',
}


/** PathSpec.PathType enum mapping. */
export enum PathSpecPathType {
  UNSET = 'UNSET',
  OS = 'OS',
  TSK = 'TSK',
  REGISTRY = 'REGISTRY',
  TMPFILE = 'TMPFILE',
  NTFS = 'NTFS',
}

/** PathSpec.Option enum mapping. */
export enum PathSpecOptions {
  CASE_INSENSITIVE = 'CASE_INSENSITIVE',
  CASE_LITERAL = 'CASE_LITERAL',
  REGEX = 'REGEX',
  RECURSIVE = 'RECURSIVE',
}

/** Mapping of the PathSpec.TskFsAttrType enum. */
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

/** PathSpec proto mapping. */
export declare interface PathSpec {
  readonly pathtype?: PathSpecPathType;
  readonly path?: string;
  readonly mountPoint?: string;
  readonly streamName?: string;
  readonly nestedPath?: PathSpec;
  readonly offset?: DecimalString;
  readonly pathOptions?: PathSpecOptions;
  readonly recursionDepth?: DecimalString;
  readonly inode?: DecimalString;
  readonly ntfsType?: PathSpecTskFsAttrType;
  readonly ntfsId?: DecimalString;
  readonly fileSizeOverride?: DecimalString;
  readonly isVirtualroot?: boolean;
}

/** MultiGetFileFlowArgs proto mapping. */
export declare interface MultiGetFileArgs {
  readonly pathspecs: ReadonlyArray<PathSpec>;
  readonly useExternalStores?: boolean;
  readonly fileSize?: DecimalString;
  readonly maximumPendingFiles?: DecimalString;
}

/** PathSpecProgress.Status enum mapping. */
export enum PathSpecProgressStatus {
  UNDEFINED = 'UNDEFINED',
  IN_PROGRESS = 'IN_PROGRESS',
  SKIPPED = 'SKIPPED',
  COLLECTED = 'COLLECTED',
  FAILED = 'FAILED',
}

/** PathSpecProgress mapping. */
export declare interface PathSpecProgress {
  readonly pathspec?: PathSpec;
  readonly status?: PathSpecProgressStatus;
}

/** MultiGetFileFlowProgress proto mapping. */
export declare interface MultiGetFileProgress {
  numPendingHashes?: number;
  numPendingFiles?: number;
  numSkipped?: number;
  numCollected?: number;
  numFailed?: number;

  pathspecsProgress: ReadonlyArray<PathSpecProgress>;
}

/** CollectBrowserHistoryResult.Browser proto enum mapping. */
export enum CollectBrowserHistoryArgsBrowser {
  UNDEFINED = 'UNDEFINED',
  CHROME = 'CHROME',
  FIREFOX = 'FIREFOX',
  INTERNET_EXPLORER = 'INTERNET_EXPLORER',
  OPERA = 'OPERA',
  SAFARI = 'SAFARI',
}

/** CollectBrowserHistoryArgs proto mapping. */
export declare interface CollectBrowserHistoryArgs {
  readonly browsers?: ReadonlyArray<CollectBrowserHistoryArgsBrowser>;
}

/** CollectBrowserHistoryResult proto mapping. */
export declare interface CollectBrowserHistoryResult {
  readonly browser?: CollectBrowserHistoryArgsBrowser;
  readonly statEntry?: StatEntry;
}

/** BrowserProgress.Status proto enum mapping. */
export enum BrowserProgressStatus {
  UNDEFINED = 'UNDEFINED',
  IN_PROGRESS = 'IN_PROGRESS',
  SUCCESS = 'SUCCESS',
  ERROR = 'ERROR',
}

/** BrowserProgress proto mapping. */
export declare interface BrowserProgress {
  readonly browser?: CollectBrowserHistoryArgsBrowser;
  readonly status?: BrowserProgressStatus;
  readonly description?: string;
  readonly numCollectedFiles?: number;
  readonly flowId?: string;
}

/** CollectBrowserHistoryProgress proto mapping. */
export declare interface CollectBrowserHistoryProgress {
  readonly browsers?: ReadonlyArray<BrowserProgress>;
}

/** CollectSingleFileArgs proto mapping. */
export declare interface CollectSingleFileArgs {
  readonly path?: string;
  readonly maxSizeBytes?: DecimalString;
}

/** CollectSingleFileResult proto mapping. */
export declare interface CollectSingleFileResult {
  readonly stat?: StatEntry;
  readonly hash?: Hash;
}

/** CollectSingleFileProgress.Status proto enum mapping. */
export enum CollectSingleFileProgressStatus {
  UNDEFINED = 'UNDEFINED',
  IN_PROGRESS = 'IN_PROGRESS',
  COLLECTED = 'COLLECTED',
  NOT_FOUND = 'NOT_FOUND',
  FAILED = 'FAILED',
}

/** CollectSingleFileProgress proto mapping. */
export declare interface CollectSingleFileProgress {
  readonly status?: CollectSingleFileProgressStatus;
  readonly result?: CollectSingleFileResult;
  readonly errorDescription?: string;
}

/** RegistryType proto mapping. */
export enum RegistryType {
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

/** StatEntry proto mapping. */
export declare interface StatEntry {
  readonly stMode?: string;
  readonly stIno?: DecimalString;
  readonly stDev?: DecimalString;
  readonly stNlink?: DecimalString;
  readonly stUid?: number;
  readonly stGid?: number;
  readonly stSize?: DecimalString;
  readonly stAtime?: DecimalString;
  readonly stMtime?: DecimalString;
  readonly stCtime?: DecimalString;
  readonly stBtime?: DecimalString;

  readonly stBlocks?: DecimalString;
  readonly stBlksize?: DecimalString;
  readonly stRdev?: DecimalString;
  readonly stFlagsOsx?: number;
  readonly stFlagsLinux?: number;

  readonly symlink?: string;
  readonly registryType?: RegistryType;

  readonly pathspec?: PathSpec;
}


/** AuthenticodeSignedData proto mapping. */
export declare interface AuthenticodeSignedData {
  readonly revision?: DecimalString;
  readonly certType?: DecimalString;
  readonly certificate: ByteString;
}

/** Hash proto mapping. */
export declare interface Hash {
  readonly sha256?: ByteString;
  readonly sha1?: ByteString;
  readonly md5?: ByteString;
  readonly pecoffSha1?: ByteString;
  readonly pecoffMd5?: ByteString;
  readonly pecoffSha256?: ByteString;

  readonly signedData?: AuthenticodeSignedData;

  readonly numBytes?: DecimalString;
  readonly sourceOffset?: DecimalString;
}

/** FileFinderContentsLiteralMatchCondition proto mapping. */
export declare interface FileFinderContentsLiteralMatchCondition {
  readonly literal?: ByteString;
  readonly mode?: FileFinderContentsMatchConditionMode;
}

/** FileFinderContentsRegexMatchCondition proto mapping. */
export declare interface FileFinderContentsRegexMatchCondition {
  readonly regex?: ByteString;
  readonly mode?: FileFinderContentsMatchConditionMode;
  readonly length?: DecimalString;
}

/** FileFinderContentsMatchConditionMode proto mapping. */
export enum FileFinderContentsMatchConditionMode {
  ALL_HITS = 0,
  FIRST_HIT = 1
}

/** FileFinderModificationTimeCondition proto mapping. */
export declare interface FileFinderModificationTimeCondition {
  readonly minLastModifiedTime?: DecimalString;
  readonly maxLastModifiedTime?: DecimalString;
}

/** FileFinderAccessTimeCondition proto mapping. */
export declare interface FileFinderAccessTimeCondition {
  readonly minLastAccessTime?: DecimalString;
  readonly maxLastAccessTime?: DecimalString;
}

/** FileFinderInodeChangeTimeCondition proto mapping. */
export declare interface FileFinderInodeChangeTimeCondition {
  readonly minLastInodeChangeTime?: DecimalString;
  readonly maxLastInodeChangeTime?: DecimalString;
}

/** FileFinderSizeCondition proto mapping. */
export declare interface FileFinderSizeCondition {
  readonly minFileSize?: DecimalString;
  readonly maxFileSize?: DecimalString;
}

/** FileFinderExtFlagsCondition proto mapping. */
export declare interface FileFinderExtFlagsCondition {
  readonly linuxBitsSet?: number;
  readonly linuxBitsUnset?: number;
  readonly osxBitsSet?: number;
  readonly osxBitsUnset?: number;
}

/** FileFinderAction.Action proto mapping. */
export enum FileFinderActionAction {
  STAT = 'STAT',
  HASH = 'HASH',
  DOWNLOAD = 'DOWNLOAD',
}


/** FileFinderAction proto mapping. */
export interface FileFinderAction {
  readonly actionType?: FileFinderActionAction;
  // Not implemented while unused in UIv2: hash, download, stat.
}

/** FileFinderArgs proto mapping. */
export declare interface FileFinderArgs {
  readonly paths?: ReadonlyArray<string>;
  readonly pathtype?: PathSpecPathType;
  readonly action?: FileFinderAction;
  // Not implemented while unused in UIv2: process_non_regular_files,
  // follow_links, conditions, xdev, implementation_type.
}

/** CollectMultipleFilesArgs proto mapping. */
export declare interface CollectMultipleFilesArgs {
  readonly pathExpressions?: ReadonlyArray<string>;

  readonly contentsLiteralMatch?: FileFinderContentsLiteralMatchCondition;
  readonly contentsRegexMatch?: FileFinderContentsRegexMatchCondition;

  readonly modificationTime?: FileFinderModificationTimeCondition;
  readonly accessTime?: FileFinderAccessTimeCondition;
  readonly inodeChangeTime?: FileFinderInodeChangeTimeCondition;
  readonly size?: FileFinderSizeCondition;
  readonly extFlags?: FileFinderExtFlagsCondition;
}

/** CollectMultipleFilesResultStatus proto mapping. */
export enum CollectMultipleFilesResultStatus {
  UNDEFINED = 0,
  COLLECTED = 1,
  FAILED = 2
}

/** CollectMultipleFilesResult proto mapping. */
export declare interface CollectMultipleFilesResult {
  readonly stat?: StatEntry;
  readonly hash?: Hash;
  readonly status?: CollectMultipleFilesResultStatus;
  readonly error?: string;
}

/** CollectMultipleFilesProgress proto mapping. */
export declare interface CollectMultipleFilesProgress {
  readonly numFound?: DecimalString;
  readonly numInProgress?: DecimalString;
  readonly numRawFsAccessRetries?: DecimalString;
  readonly numCollected?: DecimalString;
  readonly numFailed?: DecimalString;
}

/** GlobComponentExplanation proto mapping. */
export declare interface GlobComponentExplanation {
  globExpression?: string;
  examples?: ReadonlyArray<string>;
}

/** ApiExplainGlobExpressionArgs proto mapping. */
export declare interface ApiExplainGlobExpressionArgs {
  globExpression?: string;
  exampleCount?: number;
  clientId?: string;
}

/** ApiExplainGlobExpressionResult proto mapping. */
export declare interface ApiExplainGlobExpressionResult {
  components?: ReadonlyArray<GlobComponentExplanation>;
}

/** ApiScheduledFlow proto mapping. */
export declare interface ApiScheduledFlow {
  readonly scheduledFlowId?: string;
  readonly clientId?: string;
  readonly creator?: string;
  readonly flowName?: string;
  readonly flowArgs?: AnyObject;
  // Ignoring runnerArgs for now, because it is large and unused.
  readonly createTime?: string;
  readonly error?: string;
}

/** ApiListScheduledFlowsResult proto mapping. */
export declare interface ApiListScheduledFlowsResult {
  readonly scheduledFlows?: ReadonlyArray<ApiScheduledFlow>;
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

/** ApiListApproverSuggestionsResult proto mapping. */
export declare interface ApiListApproverSuggestionsResult {
  readonly suggestions?: ReadonlyArray<ApproverSuggestion>;
}

/** ApproverSuggestion proto mapping. */
export declare interface ApproverSuggestion {
  readonly username?: string;
}

/**
 * Interface for the `NetstatArgs` proto message.
 */
export declare interface NetstatArgs {
  readonly listeningOnly?: boolean;
}

/** OsqueryFlowArgs proto mapping. */
export declare interface OsqueryFlowArgs {
  readonly query?: string;
  readonly timeoutMillis?: DecimalString;
  readonly ignoreStderrErrors?: boolean;
  readonly fileCollectionColumns?: ReadonlyArray<string>;
}

/** OsqueryProgress proto mapping */
export declare interface OsqueryProgress {
  readonly partialTable?: OsqueryTable;
  readonly totalRowCount?: DecimalString;
  readonly errorMessage?: string;
}

/** OsqueryResult proto mapping. */
export declare interface OsqueryResult {
  readonly table?: OsqueryTable;
  readonly stderr?: string;
}

/** OsqueryTable proto mapping */
export declare interface OsqueryTable {
  readonly query?: string;
  readonly header?: OsqueryHeader;
  readonly rows?: ReadonlyArray<OsqueryRow>;
}

/** OsqueryHeader proto mapping */
export declare interface OsqueryHeader {
  readonly columns?: ReadonlyArray<OsqueryColumn>;
}

/** OsqueryColumn proto mapping. */
export declare interface OsqueryColumn {
  readonly name?: string;
  readonly type?: OsqueryType;
}

/**
 * OsqueryColumn.type enum proto mapping.
 */
export enum OsqueryType {
  UNKNOWN = 0,
  TEXT = 1,
  INTEGER = 2,
  BIGINT = 3,
  UNSIGNED_BIGINT = 4,
  DOUBLE = 5,
  BLOB = 6,
}

/** OsqueryRow proto mapping. */
export declare interface OsqueryRow {
  readonly values?: ReadonlyArray<string>;
}

/**
 * Interface for the `TimelineArgs` proto message.
 */
export declare interface TimelineArgs {
  /*
   * TODO: The timeline flow works with arbitrary byte paths. How
   * to support this in the user interface is yet to be designed.
   */
  readonly root?: string;
}

/** Artifact proto mapping. */
export declare interface Artifact {
  readonly name?: string;
  readonly doc?: string;
  readonly labels?: ReadonlyArray<string>;
  readonly supportedOs?: ReadonlyArray<string>;
  readonly urls?: ReadonlyArray<string>;
  readonly provides?: ReadonlyArray<string>;
  readonly sources?: ReadonlyArray<ArtifactSource>;
}

/** ArtifactDescriptor proto mapping. */
export declare interface ArtifactDescriptor {
  readonly artifact?: Artifact;
  readonly dependencies?: ReadonlyArray<string>;
  readonly pathDependencies?: ReadonlyArray<string>;
  readonly isCustom?: boolean;
}

/** SourceType proto mapping. */
export enum SourceType {
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

/** ArtifactSource proto mapping. */
export declare interface ArtifactSource {
  readonly type?: SourceType;
  readonly attributes?: Dict;
  readonly conditions?: ReadonlyArray<string>;
  readonly returnedTypes?: ReadonlyArray<string>;
  readonly supportedOs?: ReadonlyArray<string>;
}

/** ApiListArtifactsResult proto mapping. */
export declare interface ApiListArtifactsResult {
  readonly items?: ReadonlyArray<ArtifactDescriptor>;
}

/** Dict proto mapping. */
export declare interface Dict {
  readonly dat?: ReadonlyArray<KeyValue>;
}

/** KeyValue proto mapping. */
export declare interface KeyValue {
  k?: DataBlob;
  v?: DataBlob;
}

/** BlobArray proto mapping. */
export declare interface BlobArray {
  readonly content?: ReadonlyArray<DataBlob>;
}

/** DataBlob proto mapping. */
export declare interface DataBlob {
  integer?: DecimalString;
  string?: string;
  none?: string;
  boolean?: boolean;
  list?: BlobArray;
  dict?: Dict;
  float?: number;
  set?: BlobArray;
}

/** ArtifactCollectorFlowArgs.Dependency proto mapping. */
export enum ArtifactCollectorFlowArgsDependency {
  USE_CACHED = 'USE_CACHED',
  IGNORE_DEPS = 'IGNORE_DEPS',
  FETCH_NOW = 'FETCH_NOW',
}

/** ArtifactCollectorFlowArgs proto mapping. */
export declare interface ArtifactCollectorFlowArgs {
  artifactList?: string[];
  useRawFilesystemAccess?: boolean;
  splitOutputByArtifact?: boolean;
  errorOnNoResults?: boolean;
  applyParsers?: boolean;
  maxFileSize?: DecimalString;
  dependencies?: ArtifactCollectorFlowArgsDependency;
  ignoreInterpolationErrors?: boolean;
  oldClientSnapshotFallback?: boolean;
  recollectKnowledgeBase?: boolean;
}

/** Process proto mapping. */
export declare interface Process {
  readonly pid?: number;
  readonly ppid?: number;
  readonly name?: string;
  readonly exe?: string;
  readonly cmdline?: ReadonlyArray<string>;
  readonly ctime?: DecimalString;
  readonly realUid?: number;
  readonly effectiveUid?: number;
  readonly savedUid?: number;
  readonly realGid?: number;
  readonly effectiveGid?: number;
  readonly savedGid?: number;
  readonly username?: string;
  readonly terminal?: string;
  readonly status?: string;
  readonly nice?: number;
  readonly cwd?: string;
  readonly numThreads?: number;
  readonly userCpuTime?: number;
  readonly systemCpuTime?: number;
  readonly cpuPercent?: number;
  readonly rssSize?: DecimalString;
  readonly vmsSize?: DecimalString;
  readonly memoryPercent?: number;
  readonly openFiles?: ReadonlyArray<string>;
  readonly connections?: ReadonlyArray<unknown>;
}

/** ExecuteRequest proto mapping. */
export declare interface ExecuteRequest {
  readonly cmd?: string;
  readonly args?: ReadonlyArray<string>;
  // An execution time limit, given in seconds.
  readonly timeLimit?: number;
}

/** ExecuteResponse proto mapping. */
export declare interface ExecuteResponse {
  readonly request?: ExecuteRequest;
  readonly exitStatus?: number;
  readonly stdout?: ByteString;
  readonly stderr?: ByteString;
  // The time used to execute the cmd, given in microseconds.
  readonly timeUsed?: number;
}

/** ArtifactProgress proto mapping. */
export declare interface ArtifactProgress {
  readonly name?: string;
  readonly numResults?: number;
}

/** ArtifactCollectorFlowProgress proto mapping. */
export declare interface ArtifactCollectorFlowProgress {
  readonly artifacts?: ReadonlyArray<ArtifactProgress>;
}

/** `ListNamedPipesFlowArgs.PipeTypeFilter` proto mapping. */
export enum PipeTypeFilter {
  ANY_TYPE = 'ANY_TYPE',
  BYTE_TYPE = 'BYTE_TYPE',
  MESSAGE_TYPE = 'MESSAGE_TYPE',
}

/** `ListNamedPipesFlowArgs.PipeEndFilter` proto mapping. */
export enum PipeEndFilter {
  ANY_END = 'ANY_END',
  CLIENT_END = 'CLIENT_END',
  SERVER_END = 'SERVER_END',
}

/** `ListNamedPipesFlowArgs` proto mapping. */
export declare interface ListNamedPipesFlowArgs {
  readonly pipeNameRegex?: string;
  readonly procExeRegex?: string;
  readonly pipeTypeFilter?: PipeTypeFilter;
  readonly pipeEndFilter?: PipeEndFilter;
}

/** ListProcessesArgs proto mapping. */
export declare interface ListProcessesArgs {
  readonly filenameRegex?: string;
  readonly fetchBinaries?: boolean;
  readonly connectionStates?: ReadonlyArray<NetworkConnectionState>;
  readonly pids?: ReadonlyArray<number>;
}

/** NetworkEndpoint proto mapping */
export declare interface NetworkEndpoint {
  readonly ip?: string;
  readonly port?: number;
}

/** NetworkConnection.State proto mapping */
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

/** NetworkConnection.Family proto mapping */
export enum NetworkConnectionFamily {
  INET = 'INET',
  INET6 = 'INET6',
  INET6_WIN = 'INET6_WIN',
  INET6_OSX = 'INET6_OSX',
}

/** NetworkConnection.Type proto mapping */
export enum NetworkConnectionType {
  UNKNOWN_SOCKET = 'UNKNOWN_SOCKET',
  SOCK_STREAM = 'SOCK_STREAM',
  SOCK_DGRAM = 'SOCK_DGRAM',
}

/** NetworkConnection proto mapping */
export declare interface NetworkConnection {
  readonly family?: NetworkConnectionFamily;
  readonly type?: NetworkConnectionType;
  readonly localAddress?: NetworkEndpoint;
  readonly remoteAddress?: NetworkEndpoint;
  readonly state?: NetworkConnectionState;
  readonly pid?: number;
  readonly ctime?: number;
  readonly processName?: string;
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

/** ApiGetFileTextArgs proto mapping */
export declare interface ApiGetFileTextArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly offset?: DecimalString;
  readonly length?: DecimalString;
  readonly encoding?: ApiGetFileTextArgsEncoding;
  readonly timestamp?: DecimalString;
}

/** ApiGetFileBlobArgs proto mapping */
export declare interface ApiGetFileBlobArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly offset?: DecimalString;
  readonly length?: DecimalString;
  readonly timestamp?: DecimalString;
}

/** ApiGetFileTextResult proto mapping. */
export declare interface ApiGetFileTextResult {
  readonly content?: string;
  readonly totalSize?: DecimalString;
}

/** ApiFile proto mapping. */
export declare interface ApiFile {
  readonly name?: string;
  readonly path?: string;
  readonly type?: string;
  readonly stat?: StatEntry;
  readonly age?: DecimalString;
  readonly isDirectory?: boolean;
  readonly hash?: Hash;
  readonly lastCollected?: DecimalString;
  readonly lastCollectedSize?: DecimalString;

  // Not mapping the very generic ApiAff4ObjectRepresentation unless the
  // contained data is really useful for the new UI.
  // readonly details?: ApiAff4ObjectRepresentation;
}

/** ApiGetFileDetailsResult proto mapping. */
export declare interface ApiGetFileDetailsResult {
  readonly file?: ApiFile;
}

/** ApiUpdateVfsFileContentArgs proto mapping. */
export declare interface ApiUpdateVfsFileContentArgs {
  clientId?: string;
  filePath?: string;
}

/** ApiUpdateVfsFileContentResult proto mapping. */
export declare interface ApiUpdateVfsFileContentResult {
  operationId?: string;
}

/** ApiGetVfsFileContentUpdateStateArgs proto mapping. */
export declare interface ApiGetVfsFileContentUpdateStateArgs {
  clientId?: string;
  operationId?: string;
}

/** ApiGetVfsFileContentUpdateStateResult.State proto mapping. */
export enum ApiGetVfsFileContentUpdateStateResultState {
  RUNNING = 'RUNNING',
  FINISHED = 'FINISHED',
}

/** ApiGetVfsFileContentUpdateStateResult proto mapping. */
export declare interface ApiGetVfsFileContentUpdateStateResult {
  state?: ApiGetVfsFileContentUpdateStateResultState;
}

/** FlowResultCount proto mapping. */
export declare interface FlowResultCount {
  readonly type?: string;
  readonly tag?: string;
  readonly count?: DecimalString;
}

/** FlowResultMetadata proto mapping. */
export declare interface FlowResultMetadata {
  readonly numResultsPerTypeTag?: ReadonlyArray<FlowResultCount>;
  readonly isMetadataSet?: boolean;
}

/** ListDirectoryArgs proto mapping. */
export declare interface ListDirectoryArgs {
  readonly pathspec?: PathSpec;
}

/** RecursiveListDirectoryArgs proto mapping. */
export declare interface RecursiveListDirectoryArgs {
  readonly pathspec?: PathSpec;
  readonly maxDepth?: DecimalString;
}

/** ApiListFilesArgs proto mapping. */
export declare interface ApiListFilesArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly offset?: DecimalString;
  readonly count?: DecimalString;
  readonly filter?: string;
  readonly directoriesOnly?: boolean;
  readonly timestamp?: DecimalString;
}

/** ApiListFilesResult proto mapping. */
export declare interface ApiListFilesResult {
  readonly items?: ReadonlyArray<ApiFile>;
}

/** ApiBrowseFilesystemEntry proto mapping. */
export declare interface ApiBrowseFilesystemEntry {
  readonly path?: string;
  readonly children?: ReadonlyArray<ApiFile>;
}

/** ApiBrowseFilesystemResult proto mapping. */
export declare interface ApiBrowseFilesystemResult {
  readonly items?: ReadonlyArray<ApiBrowseFilesystemEntry>;
}

/** ApiCreateVfsRefreshOperationArgs proto mapping. */
export declare interface ApiCreateVfsRefreshOperationArgs {
  readonly clientId?: string;
  readonly filePath?: string;
  readonly maxDepth?: DecimalString;
  readonly notifyUser?: boolean;
}

/** ApiCreateVfsRefreshOperationResult proto mapping. */
export declare interface ApiCreateVfsRefreshOperationResult {
  readonly operationId?: string;
}

/** ApiGetVfsRefreshOperationStateArgs proto mapping. */
export declare interface ApiGetVfsRefreshOperationStateArgs {
  readonly clientId?: string;
  readonly operationId?: string;
}

/** ApiGetVfsRefreshOperationStateResult.State proto mapping. */
export enum ApiGetVfsRefreshOperationStateResultState {
  RUNNING = 'RUNNING',
  FINISHED = 'FINISHED',
}

/** ApiGetVfsRefreshOperationStateResult proto mapping. */
export declare interface ApiGetVfsRefreshOperationStateResult {
  readonly state?: ApiGetVfsRefreshOperationStateResultState;
}

/** ForemanClientRuleSetMatchMode proto mapping. */
export enum ForemanClientRuleSetMatchMode {
  MATCH_ALL = 'MATCH_ALL',
  MATCH_ANY = 'MATCH_ANY',
}

/** ForemanClientRuleType proto mapping. */
export enum ForemanClientRuleType {
  OS = 'OS',
  LABEL = 'LABEL',
  REGEX = 'REGEX',
  INTEGER = 'INTEGER',
}

/** ForemanLabelClientRuleMatchMode proto mapping. */
export enum ForemanLabelClientRuleMatchMode {
  MATCH_ALL = 'MATCH_ALL',
  MATCH_ANY = 'MATCH_ANY',
  DOES_NOT_MATCH_ALL = 'DOES_NOT_MATCH_ALL',
  DOES_NOT_MATCH_ANY = 'DOES_NOT_MATCH_ANY',
}

/** ForemanRegexClientRuleForemanStringField proto mapping. */
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

/** ForemanIntegerClientRuleOperator proto mapping. */
export enum ForemanIntegerClientRuleOperator {
  EQUAL = 'EQUAL',
  LESS_THAN = 'LESS_THAN',
  GREATER_THAN = 'GREATER_THAN',
}

/** ApiForemanIntegerClientRuleForemanIntegerField proto mapping. */
export enum ForemanIntegerClientRuleForemanIntegerField {
  UNSET = 'UNSET',
  INSTALL_TIME = 'INSTALL_TIME',
  CLIENT_VERSION = 'CLIENT_VERSION',
  LAST_BOOT_TIME = 'LAST_BOOT_TIME',
  CLIENT_CLOCK = 'CLIENT_CLOCK',
}

/** ForemanOsClientRule proto mapping. */
export declare interface ForemanOsClientRule {
  readonly osWindows?: boolean;
  readonly osLinux?: boolean;
  readonly osDarwin?: boolean;
}

/** ForemanLabelClientRule proto mapping. */
export declare interface ForemanLabelClientRule {
  readonly labelNames?: ReadonlyArray<string>;
  readonly matchMode?: ForemanLabelClientRuleMatchMode;
}

/** ForemanRegexClientRule proto mapping. */
export declare interface ForemanRegexClientRule {
  readonly attributeRegex?: string;
  readonly field?: ForemanRegexClientRuleForemanStringField;
}

/** ForemanIntegerClientRule proto mapping. */
export declare interface ForemanIntegerClientRule {
  readonly operator?: ForemanIntegerClientRuleOperator;
  readonly value?: DecimalString;
  readonly field?: ForemanIntegerClientRuleForemanIntegerField;
}

/** ForemanClientRule proto mapping. */
export declare interface ForemanClientRule {
  readonly ruleType?: ForemanClientRuleType;
  readonly os?: ForemanOsClientRule;
  readonly label?: ForemanLabelClientRule;
  readonly regex?: ForemanRegexClientRule;
  readonly integer?: ForemanIntegerClientRule;
}

/** ForemanClientRuleSet proto mapping. */
export declare interface ForemanClientRuleSet {
  readonly matchMode?: ForemanClientRuleSetMatchMode;
  readonly rules?: ReadonlyArray<ForemanClientRule>;
}

/** OutputPluginDescriptor proto mapping. */
export declare interface OutputPluginDescriptor {
  readonly pluginName?: string;
  readonly args?: AnyObject;
}

/** HuntRunnerArgs proto mapping. */
export declare interface HuntRunnerArgs {
  readonly description?: string;
  readonly clientRuleSet?: ForemanClientRuleSet;
  readonly cpuLimit?: DecimalString;
  readonly networkBytesLimit?: DecimalString;
  readonly clientRate?: number;
  readonly crashLimit?: DecimalString;
  readonly avgResultsPerClientLimit?: DecimalString;
  readonly avgCpuSecondsPerClientLimit?: DecimalString;
  readonly avgNetworkBytesPerClientLimit?: DecimalString;
  readonly expiryTime?: DecimalString;
  readonly clientLimit?: DecimalString;
  readonly outputPlugins?: ReadonlyArray<OutputPluginDescriptor>;
}

/** ApiFlowReference proto mapping. */
export declare interface ApiFlowReference {
  readonly clientId?: string;
  readonly flowId?: string;
}

/** ApiCreateHuntArgs proto mapping. */
export declare interface ApiCreateHuntArgs {
  readonly flowName?: string;
  readonly flowArgs?: AnyObject;
  readonly huntRunnerArgs?: HuntRunnerArgs;
  readonly originalFlow?: ApiFlowReference;
}

/** ApiHunt proto mapping. */
export declare interface ApiHunt {
  readonly huntId?: string;
  readonly description?: string;
  readonly creator?: string;
}

/** ApiHuntApproval proto mapping. */
export declare interface ApiHuntApproval {
  readonly subject?: ApiHunt;
  readonly id?: string;
  readonly requestor?: string;
  readonly reason?: string;
  readonly isValid?: boolean;
  readonly isValidMessage?: string;
  readonly notifiedUsers?: ReadonlyArray<string>;
  readonly approvers?: ReadonlyArray<string>;
  readonly emailCcAddresses?: ReadonlyArray<string>;
  readonly copiedFromFlow?: ApiFlow;
}

/** ApiCreateHuntApprovalArgs proto mapping. */
export declare interface ApiCreateHuntApprovalArgs {
  readonly huntId?: string;
  readonly approval?: ApiHuntApproval;
}

/**
 * Interface for the `ReadLowLevelArgs` proto message.
 */
export declare interface ReadLowLevelArgs {
  readonly path?: string;
  readonly length?: DecimalString;
  readonly offset?: DecimalString;
  readonly blockSize?: DecimalString;
}

/**
 * Interface for the `ReadLowLevelFlowResult` proto message.
 */
export declare interface ReadLowLevelFlowResult {
  readonly path?: string;
}

/** ApiGrrBinary.Type proto mapping. */
export enum ApiGrrBinaryType {
  PYTHON_HACK = 'PYTHON_HACK',
  EXECUTABLE = 'EXECUTABLE',
  COMPONENT_DEPRECATED = 'COMPONENT_DEPRECATED',
}

/** ApiGrrBinary proto mapping. */
export declare interface ApiGrrBinary {
  readonly type?: ApiGrrBinaryType;
  readonly path?: string;
  readonly size?: DecimalString;
  readonly timestamp?: DecimalString;
  readonly hasValidSignature?: boolean;
}

/** ApiListGrrBinariesResult proto mapping. */
export declare interface ApiListGrrBinariesResult {
  readonly items?: ReadonlyArray<ApiGrrBinary>;
}

/** LaunchBinaryArgs proto mapping. */
export declare interface LaunchBinaryArgs {
  readonly binary?: string;
  readonly commandLine?: string;
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

/** ExecuteBinaryResponse proto mapping. */
export declare interface ExecuteBinaryResponse {
  readonly exitStatus?: number;
  readonly stdout?: ByteString;
  readonly stderr?: ByteString;
  readonly timeUsed?: number;
}

/** CollectFilesByKnownPathArgs.CollectionLevel proto mapping. */
export enum CollectFilesByKnownPathArgsCollectionLevel {
  UNDEFINED = 'UNDEFINED',
  STAT = 'STAT',
  HASH = 'HASH',
  CONTENT = 'CONTENT',
}

/** CollectFilesByKnownPathArgs proto mapping. */
export declare interface CollectFilesByKnownPathArgs {
  readonly paths?: ReadonlyArray<string>;
  readonly collectionLevel?: CollectFilesByKnownPathArgsCollectionLevel;
}

/** CollectFilesByKnownPathResult.Status proto enum mapping. */
export enum CollectFilesByKnownPathResultStatus {
  UNDEFINED = 'UNDEFINED',
  IN_PROGRESS = 'IN_PROGRESS',
  COLLECTED = 'COLLECTED',
  NOT_FOUND = 'NOT_FOUND',
  FAILED = 'FAILED',
}

/** CollectFilesByKnownPathResult proto mapping. */
export declare interface CollectFilesByKnownPathResult {
  readonly stat: StatEntry;
  readonly hash?: Hash;
  readonly status: CollectFilesByKnownPathResultStatus;
  readonly error?: string;
}

/** CollectFilesByKnownPathProgress proto mapping. */
export declare interface CollectFilesByKnownPathProgress {
  readonly numInProgress?: DecimalString;
  readonly numRawFsAccessRetries?: DecimalString;
  readonly numCollected?: DecimalString;
  readonly numFailed?: DecimalString;
}

/** ApiListFlowsArgs proto mapping. */
export declare interface ApiListFlowsArgs {
  readonly clientId?: string;
  readonly offset?: DecimalString;
  readonly count?: DecimalString;
  readonly topFlowsOnly?: boolean;
  readonly minStartedAt?: DecimalString;
  readonly maxStartedAt?: DecimalString;
}

/** FileFinderResult proto mapping. */
export declare interface FileFinderResult {
  readonly statEntry?: StatEntry;
  readonly matches: ReadonlyArray<BufferReference>;
  readonly hashEntry?: Hash;
}

/** BufferReference proto mapping. */
export declare interface BufferReference {
  readonly offset?: DecimalString;
  readonly length?: DecimalString;
  readonly callback?: string;
  readonly data?: ByteString;
  readonly pathspec?: PathSpec;
}

/** OnlineNotificationArgs proto mapping. */
export declare interface OnlineNotificationArgs {
  readonly email?: string;
}

/** YaraProcessDumpArgs proto mapping. */
export declare interface YaraProcessDumpArgs {
  readonly pids?: ReadonlyArray<DecimalString>;
  readonly processRegex?: string;
  readonly ignoreGrrProcess?: boolean;
  readonly dumpAllProcesses?: boolean;
  readonly sizeLimit?: DecimalString;
  readonly chunkSize?: DecimalString;
  readonly skipSpecialRegions?: boolean;
  readonly skipMappedFiles?: boolean;
  readonly skipSharedRegions?: boolean;
  readonly skipExecutableRegions?: boolean;
  readonly skipReadonlyRegions?: boolean;
  readonly prioritizeOffsets?: ReadonlyArray<DecimalString>;
}


/** ProcessMemoryRegion proto mapping. */
export declare interface ProcessMemoryRegion {
  readonly start?: DecimalString;
  readonly size?: DecimalString;
  readonly file?: PathSpec;
  readonly isExecutable?: boolean;
  readonly isWritable?: boolean;
  readonly isReadable?: boolean;
  readonly dumpedSize?: DecimalString;
}

/** YaraProcessDumpInformation proto mapping. */
export declare interface YaraProcessDumpInformation {
  readonly process?: Process;
  readonly dumpFiles?: ReadonlyArray<PathSpec>;
  readonly error?: string;
  readonly dumpTimeUs?: DecimalString;
  readonly memoryRegions?: ReadonlyArray<ProcessMemoryRegion>;
}

/** YaraProcessDumpResponse proto mapping. */
export declare interface YaraProcessDumpResponse {
  readonly dumpedProcesses?: ReadonlyArray<YaraProcessDumpInformation>;
  readonly errors?: ReadonlyArray<ProcessMemoryError>;
}

/** ProcessMemoryError proto mapping. */
export declare interface ProcessMemoryError {
  readonly process?: Process;
  readonly error?: string;
}

/** YaraProcessScanRequest.ErrorPolicy proto mapping. */
export enum YaraProcessScanRequestErrorPolicy {
  NO_ERRORS = 'NO_ERRORS',
  ALL_ERRORS = 'ALL_ERRORS',
  CRITICAL_ERRORS = 'CRITICAL_ERRORS',
}

/** YaraProcessScanRequest.ImplementationType proto mapping. */
enum YaraProcessScanRequestImplementationType {
  DEFAULT = 'DEFAULT',
  DIRECT = 'DIRECT',
  SANDBOX = 'SANDBOX',
}

/** YaraSignatureShard proto mapping. */
export declare interface YaraSignatureShard {
  readonly index?: number;
  readonly payload?: ByteString;
}

/** YaraProcessScanRequest proto mapping. */
export declare interface YaraProcessScanRequest {
  readonly yaraSignature?: string;
  readonly yaraSignatureBlobId?: ByteString;
  readonly signatureShard?: YaraSignatureShard;
  readonly numSignatureShards?: number;
  readonly pids?: ReadonlyArray<DecimalString>;
  readonly processRegex?: string;
  readonly cmdlineRegex?: string;
  readonly includeErrorsInResults?: YaraProcessScanRequestErrorPolicy;
  readonly includeMissesInResults?: boolean;
  readonly ignoreGrrProcess?: boolean;
  readonly perProcessTimeout?: number;
  readonly overlapSize?: DecimalString;
  readonly skipSpecialRegions?: boolean;
  readonly skipMappedFiles?: boolean;
  readonly skipSharedRegions?: boolean;
  readonly skipExecutableRegions?: boolean;
  readonly skipReadonlyRegions?: boolean;
  readonly dumpProcessOnMatch?: boolean;
  readonly maxResultsPerProcess?: number;
  readonly processDumpSizeLimit?: DecimalString;
  readonly scanRuntimeLimitUs?: DecimalString;
  readonly implementationType?: YaraProcessScanRequestImplementationType;
}

/** ApiListHuntResultsArgs proto mapping. */
export declare interface ApiListHuntResultsArgs {
  readonly huntId?: string;
  readonly count?: number;
}

/** ApiHuntResult proto mapping. */
export declare interface ApiHuntResult {
  readonly clientId?: string;
  readonly payload?: AnyObject;
  readonly payloadType?: string;
  readonly timestamp?: string;
}

/** ApiListHuntResultsResult proto mapping. */
export declare interface ApiListHuntResultsResult {
  readonly items?: ReadonlyArray<ApiHuntResult>;
  readonly totalCount?: number;
  readonly count?: number;
  readonly filter?: string;
}

/** ApiListHuntsArgs proto mapping. */
export declare interface ApiListHuntsArgs {
  readonly offset?: DecimalString;
  readonly count?: DecimalString;
  readonly createdBy?: string;
  readonly descriptionContains?: string;
  readonly activeWithin?: DecimalString;
}

/** ApiListHuntsResult proto mapping. */
export declare interface ApiListHuntsResult {
  readonly items?: ReadonlyArray<ApiHunt>;
  readonly totalCount?: DecimalString;
}

/** YaraStringMatch proto mapping. */
export declare interface YaraStringMatch {
  readonly stringId?: string;
  readonly offset?: DecimalString;
  readonly data?: ByteString;
}

/** YaraMatch proto mapping. */
export declare interface YaraMatch {
  readonly ruleName?: string;
  readonly stringMatches?: ReadonlyArray<YaraStringMatch>;
}

/** YaraProcessScanMatch proto mapping. */
export declare interface YaraProcessScanMatch {
  readonly process?: Process;
  readonly match?: ReadonlyArray<YaraMatch>;
  readonly scanTimeUs?: DecimalString;
}
