/**
 * @fileoverview Functions to convert API data to internal models.
 */


import {
  Client,
  ClientApproval,
  ClientInformation,
  ClientLabel,
  ClientSnapshot,
  Filesystem,
  NetworkAddress,
  NetworkInterface,
  OsInfo,
  StartupInfo,
  StorageVolume,
  UnixVolume,
  User,
  WindowsVolume,
} from '../../models/client';
import {assertKeyTruthy} from '../../preconditions';
import * as apiInterfaces from '../api_interfaces';

import {
  createIpv4Address,
  createIpv6Address,
  createMacAddress,
  createOptionalDate,
  decodeBase64,
} from './primitive';
import {translateApproval} from './user';

function createClientLabel(label: apiInterfaces.ClientLabel): ClientLabel {
  assertKeyTruthy(label, 'owner');
  assertKeyTruthy(label, 'name');

  return {owner: label.owner, name: label.name};
}

/**
 * Constructs a ClientInformation object from the corresponding API data structure.
 */
export function translateClientInformation(
  apiClientInfo: apiInterfaces.ClientInformation,
): ClientInformation {
  let revision = undefined;
  if (apiClientInfo.revision !== undefined) {
    revision = BigInt(apiClientInfo.revision);
  }

  let buildTime: number = NaN;
  if (apiClientInfo.buildTime) {
    buildTime = Date.parse(apiClientInfo.buildTime);
  }

  return {
    clientName: apiClientInfo.clientName,
    clientVersion: apiClientInfo.clientVersion,
    revision,
    buildTime: buildTime ? new Date(buildTime) : undefined,
    clientBinaryName: apiClientInfo.clientBinaryName,
    clientDescription: apiClientInfo.clientDescription,
    timelineBtimeSupport: apiClientInfo.timelineBtimeSupport,
    sandboxSupport: apiClientInfo.sandboxSupport,
  };
}

function createOsInfo(apiUname: apiInterfaces.Uname): OsInfo {
  return {
    system: apiUname.system,
    node: apiUname.node,
    release: apiUname.release,
    version: apiUname.version,
    machine: apiUname.machine,
    kernel: apiUname.kernel,
    fqdn: apiUname.fqdn,
    installDate: createOptionalDate(apiUname.installDate),
    libcVer: apiUname.libcVer,
    architecture: apiUname.architecture,
  };
}

/**
 * Constructs a User object from the corresponding API data structure.
 */
export function translateUser(apiUser: apiInterfaces.User): User {
  return {
    username: apiUser.username,
    fullName: apiUser.fullName,
    lastLogon: createOptionalDate(apiUser.lastLogon),
    uid: apiUser.uid,
    gid: apiUser.gid,
    shell: apiUser.shell,
    homedir: apiUser.homedir,
  };
}

function createNetworkAddress(
  apiNetAddress: apiInterfaces.NetworkAddress,
): NetworkAddress {
  if (!apiNetAddress.addressType) {
    throw new Error('addressType attribute is missing.');
  }
  if (!apiNetAddress.packedBytes) {
    throw new Error('packedBytes attribute is missing.');
  }

  let addressType = 'IPv4';
  if (apiNetAddress.addressType === 'INET6') {
    addressType = 'IPv6';
  }

  const addressBytes = decodeBase64(apiNetAddress.packedBytes);

  return {
    addressType,
    ipAddress:
      addressType === 'IPv4'
        ? createIpv4Address(addressBytes)
        : createIpv6Address(addressBytes),
  };
}

/**
 * Constructs a NetworkInterface object from the corresponding API data structure.
 */
export function translateNetworkInterface(
  apiInterface: apiInterfaces.Interface,
): NetworkInterface {
  return {
    macAddress: apiInterface.macAddress
      ? createMacAddress(decodeBase64(apiInterface.macAddress))
      : undefined,
    interfaceName: apiInterface.ifname ?? undefined,
    addresses: (apiInterface.addresses ?? []).map(createNetworkAddress),
  };
}

function createOptionalWindowsVolume(
  volume?: apiInterfaces.WindowsVolume,
): WindowsVolume | undefined {
  if (volume === undefined) {
    return undefined;
  }

  return {
    attributes: volume.attributesList,
    driveLetter: volume.driveLetter,
    driveType: volume.driveType,
  };
}

function createOptionalUnixVolume(
  volume?: apiInterfaces.UnixVolume,
): UnixVolume | undefined {
  if (volume === undefined) {
    return undefined;
  }

  return {
    mountPoint: volume.mountPoint,
    mountOptions: volume.options,
  };
}

/**
 * Constructs a StorageVolume object from the corresponding API data structure.
 */
export function translateStorageVolume(
  apiVolume: apiInterfaces.Volume,
): StorageVolume {
  let totalSize = undefined;
  let freeSpace = undefined;
  let bytesPerSector = undefined;

  if (
    apiVolume.bytesPerSector !== undefined &&
    apiVolume.sectorsPerAllocationUnit !== undefined
  ) {
    if (apiVolume.totalAllocationUnits !== undefined) {
      totalSize =
        BigInt(apiVolume.bytesPerSector) *
        BigInt(apiVolume.sectorsPerAllocationUnit) *
        BigInt(apiVolume.totalAllocationUnits);
    }

    if (apiVolume.actualAvailableAllocationUnits !== undefined) {
      freeSpace =
        BigInt(apiVolume.bytesPerSector) *
        BigInt(apiVolume.sectorsPerAllocationUnit) *
        BigInt(apiVolume.actualAvailableAllocationUnits);
    }
  }

  if (apiVolume.bytesPerSector !== undefined) {
    bytesPerSector = BigInt(apiVolume.bytesPerSector);
  }

  return {
    name: apiVolume.name,
    devicePath: apiVolume.devicePath,
    fileSystemType: apiVolume.fileSystemType,
    bytesPerSector,
    totalSize,
    freeSpace,
    creationTime: createOptionalDate(apiVolume.creationTime),
    unixDetails: createOptionalUnixVolume(apiVolume.unixvolume),
    windowsDetails: createOptionalWindowsVolume(apiVolume.windowsvolume),
  };
}

/**
 * Constructs a Filesystem object from the corresponding API data structure.
 */
export function translateFilesystem(
  apiFilesystem: apiInterfaces.Filesystem,
): Filesystem {
  return {
    device: apiFilesystem.device,
    mountPoint: apiFilesystem.mountPoint,
    type: apiFilesystem.type,
    label: apiFilesystem.label,
  };
}

/**
 * Constructs a StartupInfo object from the corresponding API data structure.
 */
export function translateClientStartupInfo(
  apiStartupInfo: apiInterfaces.StartupInfo,
): StartupInfo {
  return {
    clientInfo: translateClientInformation(apiStartupInfo.clientInfo ?? {}),
    bootTime: createOptionalDate(apiStartupInfo.bootTime),
    interrogateRequested: apiStartupInfo.interrogateRequested,
    timestamp: createOptionalDate(apiStartupInfo.timestamp),
  };
}

/**
 * Constructs a ClientSnapshot object from the corresponding API data structure.
 */
export function translateClientSnapshot(
  apiClientSnapshot: apiInterfaces.ClientSnapshot,
): ClientSnapshot {
  if (!apiClientSnapshot.clientId) {
    throw new Error('clientId attribute is missing.');
  }
  return {
    clientId: apiClientSnapshot.clientId,
    sourceFlowId: apiClientSnapshot.metadata?.sourceFlowId ?? '',
    filesystems: (apiClientSnapshot.filesystems ?? []).map(translateFilesystem),
    osRelease: apiClientSnapshot.osRelease,
    osVersion: apiClientSnapshot.osVersion,
    arch: apiClientSnapshot.arch,
    installTime: createOptionalDate(apiClientSnapshot.installTime),
    knowledgeBase: apiClientSnapshot.knowledgeBase ?? {},
    users: (apiClientSnapshot.knowledgeBase?.users ?? []).map(translateUser),
    kernel: apiClientSnapshot.kernel,
    volumes: (apiClientSnapshot.volumes ?? []).map(translateStorageVolume),
    networkInterfaces: (apiClientSnapshot.interfaces ?? []).map(
      translateNetworkInterface,
    ),
    hardwareInfo: apiClientSnapshot.hardwareInfo,
    memorySize: apiClientSnapshot.memorySize
      ? BigInt(apiClientSnapshot.memorySize)
      : undefined,
    cloudInstance: apiClientSnapshot.cloudInstance,
    startupInfo: translateClientStartupInfo(
      apiClientSnapshot.startupInfo ?? {},
    ),
    timestamp: createOptionalDate(apiClientSnapshot.timestamp),
  };
}

/**
 * Constructs a Client object from the corresponding API data structure.
 */
export function translateClient(client: apiInterfaces.ApiClient): Client {
  assertKeyTruthy(client, 'clientId');

  let memorySize = undefined;
  if (client.memorySize !== undefined) {
    memorySize = BigInt(client.memorySize);
  }

  return {
    clientId: client.clientId,
    agentInfo: translateClientInformation(client.agentInfo ?? {}),
    rrgVersion: client.rrgVersion,
    labels: (client.labels ?? []).map(createClientLabel),
    knowledgeBase: client.knowledgeBase ?? {},
    osInfo: createOsInfo(client.osInfo ?? {}),
    users: (client.knowledgeBase?.users ?? []).map(translateUser),
    networkInterfaces: (client.interfaces ?? []).map(translateNetworkInterface),
    volumes: (client.volumes ?? []).map(translateStorageVolume),
    memorySize,
    firstSeenAt: createOptionalDate(client.firstSeenAt),
    lastSeenAt: createOptionalDate(client.lastSeenAt),
    lastBootedAt: createOptionalDate(client.lastBootedAt),
    lastClock: createOptionalDate(client.lastClock),
    age: createOptionalDate(client.age),
    cloudInstance: client.cloudInstance,
    hardwareInfo: client.hardwareInfo,
    sourceFlowId: client.sourceFlowId,
  };
}

/** Constructs a ClientApproval from the corresponding API data structure. */
export function translateClientApproval(
  approval: apiInterfaces.ApiClientApproval,
): ClientApproval {
  const translatedApproval = translateApproval(approval);

  assertKeyTruthy(approval, 'subject');
  const {subject} = approval;
  assertKeyTruthy(subject, 'clientId');

  return {
    ...translatedApproval,
    clientId: subject.clientId,
    subject: translateClient(subject),
  };
}

/**
 * Returns the name of the client label.
 */
export function translateClientLabel(
  apiLabel: apiInterfaces.ClientLabel,
): string {
  if (!apiLabel.name) throw new Error('name attribute is missing.');

  return apiLabel.name;
}
