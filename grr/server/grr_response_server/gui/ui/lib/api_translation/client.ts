/**
 * @fileoverview Functions to convert API data to internal models.
 */


import * as apiInterfaces from '../api/api_interfaces';
import {AgentInfo, Client, ClientApproval, ClientLabel, NetworkAddress, NetworkInterface, OsInfo, StorageVolume, UnixVolume, User, WindowsVolume} from '../models/client';
import {assertKeyTruthy} from '../preconditions';

import {createIpv4Address, createIpv6Address, createMacAddress, createOptionalDate, decodeBase64} from './primitive';
import {translateApprovalStatus} from './user';

/**
 * Get label name from API ClientLabel.
 */
export function getApiClientLabelName(apiLabel: apiInterfaces.ClientLabel):
    string {
  if (!apiLabel.name) throw new Error('name attribute is missing.');

  return apiLabel.name;
}

function createClientLabel(label: apiInterfaces.ClientLabel): ClientLabel {
  assertKeyTruthy(label, 'owner');
  assertKeyTruthy(label, 'name');

  return {owner: label.owner, name: label.name};
}

function createAgentInfo(apiAgentInfo: apiInterfaces.ClientInformation):
    AgentInfo {
  let revision = undefined;
  if (apiAgentInfo.revision !== undefined) {
    revision = BigInt(apiAgentInfo.revision);
  }

  // TODO: Remove this workarond once build_time is a proper Date.
  let buildTime: number = NaN;
  if (apiAgentInfo.buildTime) {
    buildTime = Date.parse(`${apiAgentInfo.buildTime} UTC`) ||
        Date.parse(apiAgentInfo.buildTime);
  }

  return {
    clientName: apiAgentInfo.clientName,
    clientVersion: apiAgentInfo.clientVersion,
    revision,
    buildTime: buildTime ? new Date(buildTime) : undefined,
    clientBinaryName: apiAgentInfo.clientBinaryName,
    clientDescription: apiAgentInfo.clientDescription,
    timelineBtimeSupport: apiAgentInfo.timelineBtimeSupport,
    sandboxSupport: apiAgentInfo.sandboxSupport,
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

function createUser(apiUser: apiInterfaces.User): User {
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

function createNetworkAddress(apiNetAddress: apiInterfaces.NetworkAddress):
    NetworkAddress {
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
    ipAddress: (addressType === 'IPv4') ? createIpv4Address(addressBytes) :
                                          createIpv6Address(addressBytes),
  };
}

function createNetworkInterface(apiInterface: apiInterfaces.Interface):
    NetworkInterface {
  if (!apiInterface.ifname) {
    throw new Error('ifname attribute is missing.');
  }

  return {
    macAddress: apiInterface.macAddress ?
        createMacAddress(decodeBase64(apiInterface.macAddress)) :
        undefined,
    interfaceName: apiInterface.ifname,
    addresses: (apiInterface.addresses ?? []).map(createNetworkAddress),
  };
}

function createOptionalWindowsVolume(volume?: apiInterfaces.WindowsVolume):
    WindowsVolume|undefined {
  if (volume === undefined) {
    return undefined;
  }

  return {
    attributes: volume.attributesList,
    driveLetter: volume.driveLetter,
    driveType: volume.driveType,
  };
}

function createOptionalUnixVolume(volume?: apiInterfaces.UnixVolume):
    UnixVolume|undefined {
  if (volume === undefined) {
    return undefined;
  }

  return {
    mountPoint: volume.mountPoint,
    mountOptions: volume.options,
  };
}

function createStorageVolume(apiVolume: apiInterfaces.Volume): StorageVolume {
  let totalSize = undefined;
  let freeSpace = undefined;
  let bytesPerSector = undefined;

  if (apiVolume.bytesPerSector !== undefined &&
      apiVolume.sectorsPerAllocationUnit !== undefined) {
    if (apiVolume.totalAllocationUnits !== undefined) {
      totalSize = BigInt(apiVolume.bytesPerSector) *
          BigInt(apiVolume.sectorsPerAllocationUnit) *
          BigInt(apiVolume.totalAllocationUnits);
    }

    if (apiVolume.actualAvailableAllocationUnits !== undefined) {
      freeSpace = BigInt(apiVolume.bytesPerSector) *
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
    fleetspeakEnabled: client.fleetspeakEnabled ?? false,
    agentInfo: createAgentInfo(client.agentInfo ?? {}),
    labels: (client.labels ?? []).map(createClientLabel),
    knowledgeBase: client.knowledgeBase ?? {},
    osInfo: createOsInfo(client.osInfo ?? {}),
    users: (client.users ?? []).map(createUser),
    networkInterfaces: (client.interfaces ?? []).map(createNetworkInterface),
    volumes: (client.volumes ?? []).map(createStorageVolume),
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
export function translateApproval(approval: apiInterfaces.ApiClientApproval):
    ClientApproval {
  assertKeyTruthy(approval, 'id');
  assertKeyTruthy(approval, 'subject');
  assertKeyTruthy(approval, 'reason');
  assertKeyTruthy(approval, 'requestor');
  assertKeyTruthy(approval, 'subject');

  const {subject} = approval;
  assertKeyTruthy(subject, 'clientId');

  const status =
      translateApprovalStatus(approval.isValid, approval.isValidMessage);

  return {
    status,
    approvalId: approval.id,
    clientId: subject.clientId,
    reason: approval.reason,
    requestedApprovers: approval.notifiedUsers ?? [],
    approvers: (approval.approvers ?? []).filter(u => u !== approval.requestor),
    requestor: approval.requestor,
    subject: translateClient(approval.subject),
    expirationTime: createOptionalDate(approval.expirationTimeUs),
  };
}
