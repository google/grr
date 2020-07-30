/**
 * @fileoverview Functions to convert API data to internal models.
 */

import {ApiClient, ApiClientApproval, ApiClientLabel, ApiKnowledgeBase, ApiClientInformation, ApiUname, ApiUser, ApiInterface, ApiNetworkAddress, ApiVolume, ApiWindowsVolume, ApiUnixVolume} from '../api/api_interfaces';
import {Client, ClientApproval, ClientApprovalStatus, ClientLabel, KnowledgeBase, AgentInfo, OsInfo, User, NetworkInterface, NetworkAddress, StorageVolume, WindowsVolume, UnixVolume} from '../models/client';

import {createOptionalDate, createIpv4Address, decodeBase64, createMacAddress, createIpv6Address} from './primitive';

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
  if (!label.owner) throw new Error('owner attribute is missing.');
  if (!label.name) throw new Error('name attribute is missing.');

  return {owner: label.owner, name: label.name};
}

function createAgentInfo(apiAgentInfo: ApiClientInformation): AgentInfo {
  let revision = undefined;
  if (apiAgentInfo.revision) {
    revision = BigInt(apiAgentInfo.revision);
  }
  return {
    clientName: apiAgentInfo.clientName,
    clientVersion: apiAgentInfo.clientVersion,
    revision: revision,
    buildTime: apiAgentInfo.buildTime,
    clientBinaryName: apiAgentInfo.clientBinaryName,
    clientDescription: apiAgentInfo.clientDescription,
  }
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
  }
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
  }
}

function createNetworkAddress(apiNetAddress: ApiNetworkAddress): NetworkAddress {
  if (!apiNetAddress.addressType) throw new Error('addressType attribute is missing.');
  if (!apiNetAddress.packedBytes) throw new Error('packedBytes attribute is missing.');

  let addressType = 'IPv4'
  if (apiNetAddress.addressType === 'INET6') {
    addressType = 'IPv6';
  }

  const addressBytes = decodeBase64(apiNetAddress.packedBytes);

  return {
    addressType: addressType,
    ipAddress: (addressType === 'IPv4') ? createIpv4Address(addressBytes) : createIpv6Address(addressBytes),
  }
}

function createNetworkInterface(apiInterface: ApiInterface): NetworkInterface {
  if (!apiInterface.macAddress) throw new Error('macAddress attribute is missing.');
  if (!apiInterface.ifname) throw new Error('ifname attribute is missing.');

  return {
    macAddress: createMacAddress(decodeBase64(apiInterface.macAddress)),
    interfaceName: apiInterface.ifname,
    addresses: (apiInterface.addresses || []).map(createNetworkAddress),
  }
}

function createOptionalWindowsVolume(volume?: ApiWindowsVolume): WindowsVolume | undefined {
  if (volume === undefined) {
    return undefined;
  }

  return {
    attributes: volume.attributesList,
    driveLetter: volume.driveLetter,
    driveType: volume.driveType,
  }
}

function createOptionalUnixVolume(volume?: ApiUnixVolume): UnixVolume | undefined {
  if (volume === undefined) {
    return undefined;
  }

  return {
    mountPoint: volume.mountPoint,
    mountOptions: volume.options,
  }
}

function createStorageVolume(apiVolume: ApiVolume): StorageVolume {
  let totalSize = undefined;
  let freeSpace = undefined;
  let bytesPerSector = undefined;

  if (apiVolume.bytesPerSector && apiVolume.sectorsPerAllocationUnit) {
    if (apiVolume.totalAllocationUnits) {
      totalSize = BigInt(apiVolume.bytesPerSector) *
          BigInt(apiVolume.sectorsPerAllocationUnit) * BigInt(apiVolume.totalAllocationUnits);
    }

    if (apiVolume.actualAvailableAllocationUnits) {
      freeSpace = BigInt(apiVolume.bytesPerSector) *
          BigInt(apiVolume.sectorsPerAllocationUnit) *
          BigInt(apiVolume.actualAvailableAllocationUnits);
    }
  }

  if (apiVolume.bytesPerSector) {
    bytesPerSector = BigInt(apiVolume.bytesPerSector);
  }

  return {
    name: apiVolume.name,
    devicePath: apiVolume.devicePath,
    fileSystemType: apiVolume.fileSystemType,
    bytesPerSector: bytesPerSector,
    totalSize: totalSize,
    freeSpace: freeSpace,
    creationTime: createOptionalDate(apiVolume.creationTime),
    unixDetails: createOptionalUnixVolume(apiVolume.unixvolume),
    windowsDetails: createOptionalWindowsVolume(apiVolume.windowsvolume),
  }
}

/**
 * Constructs a Client object from the corresponding API data structure.
 */
export function translateClient(client: ApiClient): Client {
  if (!client.clientId) throw new Error('clientId attribute is missing.');

  let memorySize = undefined;
  if (client.memorySize) {
    memorySize = BigInt(client.memorySize);
  }

  return {
    clientId: client.clientId,
    fleetspeakEnabled: client.fleetspeakEnabled || false,
    agentInfo: createAgentInfo(client.agentInfo || {}),
    labels: (client.labels || []).map(createClientLabel),
    knowledgeBase: createKnowledgeBase(client.knowledgeBase || {}),
    osInfo: createOsInfo(client.osInfo || {}),
    users: (client.users || []).map(createUser),
    networkInterfaces: (client.interfaces || []).map(createNetworkInterface),
    volumes: (client.volumes || []).map(createStorageVolume),
    memorySize: memorySize,
    firstSeenAt: createOptionalDate(client.firstSeenAt),
    lastSeenAt: createOptionalDate(client.lastSeenAt),
    lastBootedAt: createOptionalDate(client.lastBootedAt),
    lastClock: createOptionalDate(client.lastClock),
  };
}

/** Constructs a ClientApproval from the corresponding API data structure. */
export function translateApproval(approval: ApiClientApproval): ClientApproval {
  if (!approval.id) throw new Error('id attribute is missing.');
  if (!approval.subject) throw new Error('subject attribute is missing.');
  if (!approval.subject.clientId) {
    throw new Error('subject.clientId attribute is missing.');
  }
  if (!approval.reason) throw new Error('reason attribute is missing.');

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
    clientId: approval.subject.clientId,
    reason: approval.reason,
    requestedApprovers: approval.notifiedUsers || [],
    // Skip first approver, which is the requestor themselves.
    approvers: (approval.approvers || []).slice(1),
  };
}
