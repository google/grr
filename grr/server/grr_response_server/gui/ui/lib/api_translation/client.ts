/**
 * @fileoverview Functions to convert API data to internal models.
 */


import {ApiClient, ApiClientApproval, ApiClientInformation, ApiClientLabel, ApiInterface, ApiKnowledgeBase, ApiNetworkAddress, ApiUname, ApiUnixVolume, ApiUser, ApiVolume, ApiWindowsVolume} from '../api/api_interfaces';
import {AgentInfo, Client, ClientApproval, ClientApprovalStatus, ClientLabel, KnowledgeBase, NetworkAddress, NetworkInterface, OsInfo, StorageVolume, UnixVolume, User, WindowsVolume} from '../models/client';
import {assertKeyTruthy} from '../preconditions';

import {createDate, createIpv4Address, createIpv6Address, createMacAddress, createOptionalDate, decodeBase64} from './primitive';

function createKnowledgeBase(kb: ApiKnowledgeBase): KnowledgeBase {
  return {
    os: kb.os,
    fqdn: kb.fqdn,
    osMajorVersion: kb.osMajorVersion,
    osMinorVersion: kb.osMinorVersion,
  };
}

/**
 * Get label name from ApiClientLabel.
 */
export function getApiClientLabelName(apiLabel: ApiClientLabel): string {
  if (!apiLabel.name) throw new Error('name attribute is missing.');

  return apiLabel.name;
}

function createClientLabel(label: ApiClientLabel): ClientLabel {
  assertKeyTruthy(label, 'owner');
  assertKeyTruthy(label, 'name');

  return {owner: label.owner, name: label.name};
}

function createAgentInfo(apiAgentInfo: ApiClientInformation): AgentInfo {
  let revision = undefined;
  if (apiAgentInfo.revision !== undefined) {
    revision = BigInt(apiAgentInfo.revision);
  }

  return {
    clientName: apiAgentInfo.clientName,
    clientVersion: apiAgentInfo.clientVersion,
    revision,
    buildTime: apiAgentInfo.buildTime,
    clientBinaryName: apiAgentInfo.clientBinaryName,
    clientDescription: apiAgentInfo.clientDescription,
  };
}

function createOsInfo(apiUname: ApiUname): OsInfo {
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

function createUser(apiUser: ApiUser): User {
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

function createNetworkAddress(apiNetAddress: ApiNetworkAddress):
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

function createNetworkInterface(apiInterface: ApiInterface): NetworkInterface {
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

function createOptionalWindowsVolume(volume?: ApiWindowsVolume): WindowsVolume|
    undefined {
  if (volume === undefined) {
    return undefined;
  }

  return {
    attributes: volume.attributesList,
    driveLetter: volume.driveLetter,
    driveType: volume.driveType,
  };
}

function createOptionalUnixVolume(volume?: ApiUnixVolume): UnixVolume|
    undefined {
  if (volume === undefined) {
    return undefined;
  }

  return {
    mountPoint: volume.mountPoint,
    mountOptions: volume.options,
  };
}

function createStorageVolume(apiVolume: ApiVolume): StorageVolume {
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
export function translateClient(client: ApiClient): Client {
  assertKeyTruthy(client, 'clientId');
  assertKeyTruthy(client, 'age');

  let memorySize = undefined;
  if (client.memorySize !== undefined) {
    memorySize = BigInt(client.memorySize);
  }

  return {
    clientId: client.clientId,
    fleetspeakEnabled: client.fleetspeakEnabled ?? false,
    agentInfo: createAgentInfo(client.agentInfo ?? {}),
    labels: (client.labels ?? []).map(createClientLabel),
    knowledgeBase: createKnowledgeBase(client.knowledgeBase ?? {}),
    osInfo: createOsInfo(client.osInfo ?? {}),
    users: (client.users ?? []).map(createUser),
    networkInterfaces: (client.interfaces ?? []).map(createNetworkInterface),
    volumes: (client.volumes ?? []).map(createStorageVolume),
    memorySize,
    firstSeenAt: createOptionalDate(client.firstSeenAt),
    lastSeenAt: createOptionalDate(client.lastSeenAt),
    lastBootedAt: createOptionalDate(client.lastBootedAt),
    lastClock: createOptionalDate(client.lastClock),
    age: createDate(client.age),
  };
}

/** Constructs a ClientApproval from the corresponding API data structure. */
export function translateApproval(approval: ApiClientApproval): ClientApproval {
  assertKeyTruthy(approval, 'id');
  assertKeyTruthy(approval, 'subject');
  assertKeyTruthy(approval, 'reason');
  assertKeyTruthy(approval, 'requestor');
  assertKeyTruthy(approval, 'subject');

  const {subject} = approval;
  assertKeyTruthy(subject, 'clientId');

  let status: ClientApprovalStatus;
  if (approval.isValid) {
    status = {type: 'valid'};
  } else if (!approval.isValidMessage) {
    throw new Error('isValidMessage attribute is missing.');
  } else if (approval.isValidMessage.includes('Approval request is expired')) {
    status = {type: 'expired', reason: approval.isValidMessage};
  } else if (approval.isValidMessage.includes('Need at least')) {
    status = {type: 'pending', reason: approval.isValidMessage};
  } else {
    status = {type: 'invalid', reason: approval.isValidMessage};
  }

  return {
    status,
    approvalId: approval.id,
    clientId: subject.clientId,
    reason: approval.reason,
    requestedApprovers: approval.notifiedUsers ?? [],
    approvers: (approval.approvers ?? []).filter(u => u !== approval.requestor),
    requestor: approval.requestor,
    subject: translateClient(approval.subject),
  };
}
