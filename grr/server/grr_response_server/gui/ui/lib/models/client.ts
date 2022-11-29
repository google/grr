/**
 * @fileoverview The module provides client-related data model entities.
 */

import {DateTime, Duration} from '../../lib/date_time';
import {KnowledgeBase} from '../api/api_interfaces';
import {addToMapSetInPlace, camelToSnakeCase} from '../type_utils';

import {ApprovalStatus} from './user';



/** A KnowledgeBase key (e.g. `users.internet_cache`) with example values. */
export interface KnowledgeBaseExample {
  readonly key: string;
  readonly examples: ReadonlyArray<string>;
}

/**
 * Returns glob expression keys and substitution examples for KnowledgeBase
 * entries like %%users.homedir%%.
 */
export function getKnowledgeBaseExpressionExamples(kb: KnowledgeBase) {
  const examples = new Map<string, Set<string>>();
  compileExamples(kb, '', examples);
  return Array.from(examples.entries())
      .map(([key, values]) => ({key, examples: Array.from(values)}));
}

type KbValue =
    KnowledgeBase|KnowledgeBase[keyof KnowledgeBase]|User[keyof User];

function compileExamples(
    obj: KbValue, prefix: string, examples: Map<string, Set<string>>) {
  if (Array.isArray(obj)) {
    for (const value of obj) {
      compileExamples(value, prefix, examples);
    }
  } else if (typeof obj === 'object') {
    for (const [camelKey, value] of Object.entries(obj)) {
      const key = camelToSnakeCase(camelKey);
      const subPrefix = prefix ? `${prefix}.${key}` : key;
      compileExamples(value, subPrefix, examples);
    }
  } else {
    addToMapSetInPlace(examples, `%%${prefix}%%`, `${obj}`);
  }
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
  readonly buildTime?: Date;
  readonly clientBinaryName?: string;
  readonly clientDescription?: string;
  readonly timelineBtimeSupport?: boolean;
  readonly sandboxSupport?: boolean;
}

/**
 * Client Label.
 */
export interface ClientLabel {
  readonly owner: string;
  readonly name: string;
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
  readonly age?: Date;
  readonly cloudInstance?: CloudInstance;
  readonly hardwareInfo?: HardwareInfo;
  readonly sourceFlowId?: string;
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

/** Approval for Client access. */
export interface ClientApproval {
  readonly approvalId: string;
  readonly clientId: string;
  readonly requestor: string;
  readonly reason: string;
  readonly status: ApprovalStatus;
  readonly requestedApprovers: ReadonlyArray<string>;
  readonly approvers: ReadonlyArray<string>;
  readonly subject: Client;
  readonly expirationTime?: Date;
}

const ONLINE_THRESHOLD = Duration.fromObject({minutes: 15});

/** Returns true if `lastSeen` is considered to be online. */
export function isClientOnline(lastSeen: Date) {
  const lastSeenLuxon = DateTime.fromJSDate(lastSeen);
  return lastSeenLuxon.diffNow().negate() < ONLINE_THRESHOLD;
}

const CLIENT_ID_RE = /^[C]\.[0-9A-F]{16}$/i;

/** Returns true if the string matches a client id like "C.1e0384f90ac7c7eb". */
export function isClientId(str: string) {
  return str.match(CLIENT_ID_RE) !== null;
}
