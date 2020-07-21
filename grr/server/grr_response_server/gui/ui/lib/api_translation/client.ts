/**
 * @fileoverview Functions to convert API data to internal models.
 */

import {ApiClient, ApiClientApproval, ApiClientLabel, ApiKnowledgeBase, ApiClientInformation, ApiUname} from '../api/api_interfaces';
import {Client, ClientApproval, ClientApprovalStatus, ClientLabel, KnowledgeBase, AgentInfo, OsInfo} from '../models/client';

import {createOptionalDate} from './primitive';

function createKnowledgeBase(kb: ApiKnowledgeBase): KnowledgeBase {
  return {
    os: kb.os,
    fqdn: kb.fqdn,
    osMajorVersion: kb.osMajorVersion,
    osMinorVersion: kb.osMinorVersion,
  };
}

function createClientLabel(label: ApiClientLabel): ClientLabel {
  if (!label.owner) throw new Error('owner attribute is missing.');
  if (!label.name) throw new Error('name attribute is missing.');

  return {owner: label.owner, name: label.name};
}

function createAgentInfo(apiAgentInfo: ApiClientInformation): AgentInfo {
  return {
    clientName: apiAgentInfo.clientName || 'Unknown',
    clientVersion: apiAgentInfo.clientVersion || 0,
    revision: apiAgentInfo.revision || 0,
    buildTime: apiAgentInfo.buildTime || 'Unknown',
    clientBinaryName: apiAgentInfo.clientBinaryName || 'Unknown',
    clientDescription: apiAgentInfo.clientDescription || 'Unknown',
    labels: apiAgentInfo.labels || [],
  }
}

function createOsInfo(apiUname: ApiUname): OsInfo {
  return {
    system: apiUname.system || 'Unknown',
    node: apiUname.node || 'Unknown',
    release: apiUname.release || 'Unknown',
    version: apiUname.version || 'Unknown',
    machine: apiUname.machine || 'Unknown',
    kernel: apiUname.kernel || 'Unknown',
    fqdn: apiUname.fqdn || 'Unknown',
    installDate: createOptionalDate(apiUname.installDate),
    libcVer: apiUname.libcVer || 'Unknown',
    architecture: apiUname.architecture || 'Unknown',
    pep425tag: apiUname.pep425tag || 'Unknown',
  }
}

/**
 * Constructs a Client object from the corresponding API data structure.
 */
export function translateClient(client: ApiClient): Client {
  if (!client.clientId) throw new Error('clientId attribute is missing.');

  return {
    clientId: client.clientId,
    fleetspeakEnabled: client.fleetspeakEnabled || false,
    agentInfo: createAgentInfo(client.agentInfo || {}),
    labels: (client.labels || []).map(createClientLabel),
    knowledgeBase: createKnowledgeBase(client.knowledgeBase || {}),
    osInfo: createOsInfo(client.osInfo || {}),
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
