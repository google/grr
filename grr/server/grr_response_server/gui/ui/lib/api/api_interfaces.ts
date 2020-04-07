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
  [key: string]: undefined|null|string|number|boolean|AnyObject;
}

/**
 * KnowledgeBase proto mapping.
 */
export declare interface ApiKnowledgeBase {
  readonly fqdn?: string;
  readonly os?: string;
}

/**
 * ClientLabel proto mapping.
 */
export declare interface ApiClientLabel {
  readonly owner?: string;
  readonly name?: string;
}

/**
 * ApiClient proto mapping.
 */
export declare interface ApiClient {
  readonly clientId?: string;
  readonly urn?: string;

  readonly fleetspeakEnabled?: boolean;

  readonly knowledgeBase?: ApiKnowledgeBase;

  readonly firstSeenAt?: string;
  readonly lastSeenAt?: string;
  readonly lastBootedAt?: string;
  readonly lastClock?: string;
  readonly labels?: ReadonlyArray<ApiClientLabel>;
}

/**
 * ApiSearchClientArgs proto mapping.
 */
export declare interface ApiSearchClientArgs {
  readonly query?: string;
  readonly offset?: number;
  readonly count?: number;
}

/**
 * ApiSearchClientResult proto mapping.
 */
export declare interface ApiSearchClientResult {
  readonly items: ReadonlyArray<ApiClient>;
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
  readonly reason?: string;
  readonly isValid?: boolean;
  readonly isValidMessage?: string;
  readonly notifiedUsers?: string[];
  readonly approvers?: string[];
  readonly emailCcAddresses?: string[];
}

/** ApiListClientApprovalsResult proto mapping */
export declare interface ApiListClientApprovalsResult {
  readonly items: ApiClientApproval[];
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
  readonly items: ReadonlyArray<ApiFlowDescriptor>;
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
}

/** ApiListFlowsResult proto mapping. */
export declare interface ApiListFlowsResult {
  readonly items: ReadonlyArray<ApiFlow>;
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

/** ApiBrowserHistoryFlowArgs proto mapping. */
export declare interface ApiBrowserHistoryFlowArgs {
  collectChrome?: boolean;
  collectFirefox?: boolean;
  collectInternetExplorer?: boolean;
  collectOpera?: boolean;
  collectSafari?: boolean;
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
  readonly offset?: number;
  readonly pathOptions?: PathSpecOptions;
  readonly recursionDepth?: number;
  readonly inode?: number;
  readonly ntfsType?: PathSpecTskFsAttrType;
  readonly ntfsId?: number;
  readonly fileSizeOverride?: number;
  readonly isVirtualroot?: boolean;
}

/** MultiGetFileFlowArgs proto mapping. */
export declare interface MultiGetFileArgs {
  readonly pathspecs: PathSpec[];
  readonly useExternalStores?: boolean;
  readonly fileSize?: number;
  readonly maximumPendingFiles?: number;
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
