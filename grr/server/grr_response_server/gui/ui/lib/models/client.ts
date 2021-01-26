/**
 * @fileoverview The module provides client-related data model entities.
 */




/**
 * Client's knowledge base data.
 */
export interface KnowledgeBase {
  /** Client's FQDN. */
  readonly fqdn?: string;
  readonly os?: string;
  readonly osMajorVersion?: number;
  readonly osMinorVersion?: number;
}


/**
 * Windows specific volume details.
 */
export interface WindowsVolume {
  readonly attributes?: ReadonlyArray<string>;
  readonly driveLetter?: string;
  readonly driveType?: string;
}

/**
 * Unix specific volume details.
 */
export interface UnixVolume {
  readonly mountPoint?: string;
  readonly mountOptions?: string;
}

/**
 * Storage volume.
 */
export interface StorageVolume {
  readonly name?: string;
  readonly devicePath?: string;
  readonly fileSystemType?: string;
  readonly totalSize?: bigint;
  readonly bytesPerSector?: bigint;
  readonly freeSpace?: bigint;
  readonly creationTime?: Date;
  readonly unixDetails?: UnixVolume;
  readonly windowsDetails?: WindowsVolume;
}

/**
 * User
 */
export interface User {
  readonly username?: string;
  readonly lastLogon?: Date;
  readonly fullName?: string;
  readonly homedir?: string;
  readonly uid?: number;
  readonly gid?: number;
  readonly shell?: string;
}

/**
 * System information
 */
export interface OsInfo {
  readonly system?: string;
  readonly node?: string;
  readonly release?: string;
  readonly version?: string;
  readonly machine?: string;
  readonly kernel?: string;
  readonly fqdn?: string;
  readonly installDate?: Date;
  readonly libcVer?: string;
  readonly architecture?: string;
}

/**
 * Network Address
 */
export interface NetworkAddress {
  readonly addressType: string;
  readonly ipAddress: string;
}

/**
 * Network interface
 */
export interface NetworkInterface {
  readonly macAddress?: string;
  readonly interfaceName: string;
  readonly addresses: ReadonlyArray<NetworkAddress>;
}

/**
 * Info about the agent running on the client.
 */
export interface AgentInfo {
  readonly clientName?: string;
  readonly clientVersion?: number;
  readonly revision?: bigint;
  readonly buildTime?: string;
  readonly clientBinaryName?: string;
  readonly clientDescription?: string;
}

/**
 * Client Label.
 */
export interface ClientLabel {
  readonly owner: string;
  readonly name: string;
}

/**
 * Client.
 */
export interface Client {
  /** Client id. */
  readonly clientId: string;
  /** Whether the client communicates with GRR through Fleetspeak. */
  readonly fleetspeakEnabled: boolean;
  /** Metadata about the GRR client */
  readonly agentInfo: AgentInfo;
  /** Client's knowledge base. */
  readonly knowledgeBase: KnowledgeBase;
  /** Data about the system of the client */
  readonly osInfo: OsInfo;
  /** Users on the client */
  readonly users: ReadonlyArray<User>;
  /** Network interfaces of the client */
  readonly networkInterfaces: ReadonlyArray<NetworkInterface>;
  /** Storage volumes available to the client */
  readonly volumes: ReadonlyArray<StorageVolume>;
  /** Memory available to this client */
  readonly memorySize?: bigint;
  // TODO(user): Replace `Date` type with immutable date type.
  /** When the client was first seen. */
  readonly firstSeenAt?: Date;
  /** When the client was last seen. */
  readonly lastSeenAt?: Date;
  /** Last time the client booted. */
  readonly lastBootedAt?: Date;
  /** Last reported client clock time. */
  readonly lastClock?: Date;
  /** List of ClientLabels */
  readonly labels: ReadonlyArray<ClientLabel>;
  /** The time when this client info was born */
  readonly age: Date;
}

/** Approval Request. */
export interface ApprovalRequest {
  readonly clientId: string;
  readonly approvers: string[];
  readonly reason: string;
  readonly cc: string[];
}

/** Configuration for Client Approvals. */
export interface ApprovalConfig {
  readonly optionalCcEmail?: string;
}

/** Indicates that a ClientApproval has been granted and is currently valid. */
export interface Valid {
  readonly type: 'valid';
}

/** Indicates that a ClientApproval is pending approval from an approver. */
export interface Pending {
  readonly type: 'pending';
  readonly reason: string;
}

/** Indicates that a ClientApproval had been granted, but is expired. */
export interface Expired {
  readonly type: 'expired';
  readonly reason: string;
}

/** Indicates that a ClientApproval is invalid for other reasons. */
export interface Invalid {
  readonly type: 'invalid';
  readonly reason: string;
}

/** Status of a ClientApproval. */
export type ClientApprovalStatus = Valid|Pending|Expired|Invalid;

/** Approval for Client access. */
export interface ClientApproval {
  readonly approvalId: string;
  readonly clientId: string;
  readonly requestor: string;
  readonly reason: string;
  readonly status: ClientApprovalStatus;
  readonly requestedApprovers: ReadonlyArray<string>;
  readonly approvers: ReadonlyArray<string>;
  readonly subject: Client;
}
