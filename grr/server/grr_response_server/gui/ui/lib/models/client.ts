/**
 * @fileoverview The module provides client-related data model entities.
 */

import {DateTime, Duration} from '../../lib/date_time';
import {
  CloudInstance,
  CloudInstanceInstanceType,
  KnowledgeBase,
} from '../api/api_interfaces';
import {addToMapSetInPlace, camelToSnakeCase} from '../type_utils';

import {Approval, ApprovalRequest} from './user';



/** A KnowledgeBase key (e.g. `users.internet_cache`) with example values. */
export interface KnowledgeBaseExample {
  readonly key: string;
  readonly examples: readonly string[];
}

/**
 * Returns glob expression keys and substitution examples for KnowledgeBase
 * entries like %%users.homedir%%.
 */
export function getKnowledgeBaseExpressionExamples(kb: KnowledgeBase) {
  const examples = new Map<string, Set<string>>();
  compileExamples(kb, '', examples);
  return Array.from(examples.entries()).map(([key, values]) => ({
    key,
    examples: Array.from(values),
  }));
}

type KbValue =
  | KnowledgeBase
  | KnowledgeBase[keyof KnowledgeBase]
  | User[keyof User];

function compileExamples(
  obj: KbValue,
  prefix: string,
  examples: Map<string, Set<string>>,
) {
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
  readonly attributes?: readonly string[];
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
  readonly interfaceName?: string;
  readonly addresses: readonly NetworkAddress[];
}

/**
 * Info about the agent running on the client.
 */
export interface ClientInformation {
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
 * Filesystem information.
 */
export interface Filesystem {
  readonly device?: string;
  readonly mountPoint?: string;
  readonly type?: string;
  readonly label?: string;
}

/**
 * Client Label.
 */
export interface ClientLabel {
  readonly owner: string;
  readonly name: string;
}

/**
 * Client Warning.
 */
export interface ClientWarning {
  htmlSnippet: string;
  isClosed: boolean;
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

/** StartupInfo proto mapping. */
export interface StartupInfo {
  readonly clientInfo?: ClientInformation;
  readonly bootTime?: Date;
  readonly interrogateRequested?: boolean;
  readonly timestamp?: Date;
}

/** ClientSnapshot proto mapping. */
export interface ClientSnapshot {
  readonly clientId: string;
  readonly sourceFlowId?: string;
  readonly filesystems?: readonly Filesystem[];
  readonly osRelease?: string;
  readonly osVersion?: string;
  readonly arch?: string;
  readonly installTime?: Date;
  readonly knowledgeBase: KnowledgeBase;
  readonly users: readonly User[];
  readonly kernel?: string;
  readonly volumes: readonly StorageVolume[];
  readonly networkInterfaces: readonly NetworkInterface[];
  readonly hardwareInfo?: HardwareInfo;
  readonly memorySize?: bigint;
  readonly cloudInstance?: CloudInstance;
  readonly startupInfo?: StartupInfo;
  readonly timestamp?: Date;
}

/**
 * Client.
 */
export interface Client {
  /** Client id. */
  readonly clientId: string;
  /** Metadata about the GRR client */
  readonly agentInfo: ClientInformation;
  /** Version of the RRG agent running on the client. */
  readonly rrgVersion?: string;
  /** Client's knowledge base. */
  readonly knowledgeBase: KnowledgeBase;
  /** Data about the system of the client */
  readonly osInfo: OsInfo;
  /** Users on the client */
  readonly users: readonly User[];
  /** Network interfaces of the client */
  readonly networkInterfaces: readonly NetworkInterface[];
  /** Storage volumes available to the client */
  readonly volumes: readonly StorageVolume[];
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
  readonly labels: readonly ClientLabel[];
  /** The time when this client info was born */
  readonly age?: Date;
  readonly cloudInstance?: CloudInstance;
  readonly hardwareInfo?: HardwareInfo;
  readonly sourceFlowId?: string;
}

/** Approval Request for a client. */
export interface ClientApprovalRequest extends ApprovalRequest {
  readonly clientId: string;
  readonly expirationTimeUs?: string;
}

/** Configuration for Client Approvals. */
export interface ApprovalConfig {
  readonly optionalCcEmail?: string;
}

/** Approval for Client access. */
export interface ClientApproval extends Approval {
  readonly clientId: string;
  readonly subject: Client;
}

/** Returns true if the approval is a client approval. */
export function isClientApproval(
  approval: Approval,
): approval is ClientApproval {
  return (approval as ClientApproval).clientId !== undefined;
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

const MISSING_VALUE = '?';

/**
 * Accessor for the osRelease field.
 */
export function osReleaseAccessor(snapshot: ClientSnapshot): string {
  return snapshot.osRelease ?? MISSING_VALUE;
}

/**
 * Accessor for the osVersion field.
 */
export function osVersionAccessor(snapshot: ClientSnapshot): string {
  return snapshot.osVersion ?? MISSING_VALUE;
}

/**
 * Accessor for the kernel field.
 */
export function osKernelAccessor(snapshot: ClientSnapshot): string {
  return snapshot.kernel ?? MISSING_VALUE;
}

/**
 * Accessor for the osInstallDate field.
 */
export function osInstallDateAccessor(snapshot: ClientSnapshot): string {
  return snapshot.installTime?.toUTCString() ?? MISSING_VALUE;
}

/**
 * Accessor for the arch field.
 */
export function archAccessor(snapshot: ClientSnapshot): string {
  return snapshot.arch ?? MISSING_VALUE;
}

/**
 * Accessor for the memorySize field.
 */
export function memorySizeAccessor(snapshot: ClientSnapshot): string {
  return (String(snapshot.memorySize) ?? MISSING_VALUE) + ' bytes';
}

/**
 * Accessor for the volumes field.
 */
export function volumesAccessor(snapshot: ClientSnapshot): string {
  return (snapshot.volumes ?? [])
    .map((volume: StorageVolume) => {
      return (
        `Device path: ${volume.devicePath ?? MISSING_VALUE}` +
        `\nFile system type: ${volume.fileSystemType ?? MISSING_VALUE}` +
        `\nFree space: ${volume.freeSpace ?? MISSING_VALUE} bytes`
      );
    })
    .join(',\n\n');
}

/**
 * Accessor for the networkInterfaces field.
 */
export function networkInterfacesAccessor(snapshot: ClientSnapshot): string {
  return (snapshot.networkInterfaces ?? [])
    .map((networkInterface: NetworkInterface) => networkInterface.interfaceName)
    .join(',\n');
}

/**
 * Accessor for the startupInfo field.
 */
export function startupInfoAccessor(snapshot: ClientSnapshot): string {
  return [
    'Boot Time: ',
    snapshot.startupInfo?.bootTime?.toUTCString() ?? MISSING_VALUE,
    '\nClient Name: ',
    snapshot.startupInfo?.clientInfo?.clientName ?? MISSING_VALUE,
    '\nClient Version: ',
    snapshot.startupInfo?.clientInfo?.clientVersion ?? MISSING_VALUE,
    '\nBuild Time: ',
    snapshot.startupInfo?.clientInfo?.buildTime?.toUTCString() ?? '',
    '\nBinary Name: ',
    snapshot.startupInfo?.clientInfo?.clientBinaryName ?? MISSING_VALUE,
    '\nDescription: ',
    snapshot.startupInfo?.clientInfo?.clientDescription ?? MISSING_VALUE,
    '\nSandboxing supported: ',
    snapshot.startupInfo?.clientInfo?.sandboxSupport ?? MISSING_VALUE,
    '\nBtime supported: ',
    snapshot.startupInfo?.clientInfo?.timelineBtimeSupport ?? MISSING_VALUE,
  ].join('');
}

/**
 * Accessor for the knowledgeBase field.
 */
export function knowledgeBaseAccessor(snapshot: ClientSnapshot): string {
  return [
    'OS: ',
    snapshot.knowledgeBase?.os ?? MISSING_VALUE,
    '\nFQDN: ',
    snapshot.knowledgeBase?.fqdn ?? MISSING_VALUE,
    '\nOS Major Version: ',
    snapshot.knowledgeBase?.osMajorVersion ?? MISSING_VALUE,
    '\nOS Minor Version: ',
    snapshot.knowledgeBase?.osMinorVersion ?? MISSING_VALUE,
  ].join('');
}

/**
 * Accessor for the hardwareInfo field.
 */
export function hardwareInfoAccessor(snapshot: ClientSnapshot): string {
  return [
    'System Manufacturer: ',
    snapshot.hardwareInfo?.systemManufacturer ?? MISSING_VALUE,
    '\nSystem Family: ',
    snapshot.hardwareInfo?.systemFamily ?? MISSING_VALUE,
    '\nSystem Product Name: ',
    snapshot.hardwareInfo?.systemProductName ?? MISSING_VALUE,
    '\nSerial Number: ',
    snapshot.hardwareInfo?.serialNumber ?? MISSING_VALUE,
    '\nSystem UUID: ',
    snapshot.hardwareInfo?.systemUuid ?? MISSING_VALUE,
    '\nSystem SKU Number: ',
    snapshot.hardwareInfo?.systemSkuNumber ?? MISSING_VALUE,
    '\nSystem Assettag: ',
    snapshot.hardwareInfo?.systemAssettag ?? MISSING_VALUE,
    '\nBIOS Vendor: ',
    snapshot.hardwareInfo?.biosVendor ?? MISSING_VALUE,
    '\nBIOS Version: ',
    snapshot.hardwareInfo?.biosVersion ?? MISSING_VALUE,
    '\nBIOS Release Date: ',
    snapshot.hardwareInfo?.biosReleaseDate ?? MISSING_VALUE,
    '\nBIOS ROM Size: ',
    snapshot.hardwareInfo?.biosRomSize ?? MISSING_VALUE,
    '\nBIOS Revision: ',
    snapshot.hardwareInfo?.biosRevision ?? MISSING_VALUE,
  ].join('');
}

/**
 * Accessor for the cloudInstance field.
 */
export function cloudInstanceAccessor(snapshot: ClientSnapshot): string {
  const cloudType = snapshot.cloudInstance?.cloudType;
  if (cloudType === CloudInstanceInstanceType.AMAZON) {
    return [
      'Instance ID: ',
      snapshot.cloudInstance?.amazon?.instanceId ?? MISSING_VALUE,
      '\nHostname: ',
      snapshot.cloudInstance?.amazon?.hostname ?? MISSING_VALUE,
      '\nPublic hostname: ',
      snapshot.cloudInstance?.amazon?.publicHostname ?? MISSING_VALUE,
      '\nAMI ID: ',
      snapshot.cloudInstance?.amazon?.amiId ?? MISSING_VALUE,
      '\nInstance type: ',
      snapshot.cloudInstance?.amazon?.instanceType ?? MISSING_VALUE,
    ].join('');
  }
  if (cloudType === CloudInstanceInstanceType.GOOGLE) {
    return [
      'Unique ID: ',
      snapshot.cloudInstance?.google?.uniqueId ?? MISSING_VALUE,
      '\nZone: ',
      snapshot.cloudInstance?.google?.zone ?? MISSING_VALUE,
      '\nProject ID: ',
      snapshot.cloudInstance?.google?.projectId ?? MISSING_VALUE,
      '\nInstance ID: ',
      snapshot.cloudInstance?.google?.instanceId ?? MISSING_VALUE,
      '\nHostname: ',
      snapshot.cloudInstance?.google?.hostname ?? MISSING_VALUE,
      '\nMachine Type: ',
      snapshot.cloudInstance?.google?.machineType ?? MISSING_VALUE,
    ].join('');
  }
  return '';
}

/**
 * Accessor for the users field.
 */
export function usersAccessor(snapshot: ClientSnapshot): string {
  return (snapshot.users ?? []).map((user: User) => user.username).join(',\n');
}
