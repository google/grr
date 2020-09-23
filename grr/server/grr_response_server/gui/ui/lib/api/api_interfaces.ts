/**
 * @fileoverview The module provides mappings for GRR API protos (in JSON
 * format) into TypeScript interfaces. They are not indended to be
 * complete: only actually used fields are mapped.
 *
 * TODO(user): Using Protobuf-code generation insted of manually writing
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
export type DecimalString = string|number;

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

/**
 * ApiClient proto mapping.
 */
export declare interface ApiClient {
  readonly clientId?: string;
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
  readonly pathspecs: PathSpec[];
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

  pathspecsProgress: PathSpecProgress[];
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

/** StatEntry proto mapping. */
export declare interface StatEntry {
  readonly stMode?: string;
  readonly stIno?: number;
  readonly stDev?: number;
  readonly stNlink?: number;
  readonly stUid?: number;
  readonly stGid?: number;
  readonly stSize?: string;
  readonly stAtime?: string;
  readonly stMtime?: string;
  readonly stCtime?: string;
  readonly stCrtime?: string;

  readonly stBlocks?: number;
  readonly stBlksize?: number;
  readonly stRdev?: number;
  readonly stFlagsOsx?: number;
  readonly stFlagsLinux?: number;

  readonly symlink?: string;

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

/** CollectMultipleFilesArgs proto mapping. */
export declare interface CollectMultipleFilesArgs {
  pathExpressions?: ReadonlyArray<string>;
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
}

/** ApiListApproverSuggestionsResult proto mapping. */
export declare interface ApiListApproverSuggestionsResult {
  readonly suggestions?: ReadonlyArray<ApproverSuggestion>;
}

/** ApproverSuggestion proto mapping. */
export declare interface ApproverSuggestion {
  readonly username?: string;
}
