import {Approval, ApprovalStatus, GrrUser} from '../../models/user';
import {assertKeyTruthy} from '../../preconditions';
import {
  ApiClientApproval,
  ApiGrrUser,
  ApiGrrUserUserType,
  ApiHuntApproval,
  ApiListApproverSuggestionsResultApproverSuggestion,
} from '../api_interfaces';
import {createOptionalDate} from './primitive';

/** Translates API ApiGrrUser object into the model's GrrUser. */
export function translateGrrUser(apiGrrUser: ApiGrrUser): GrrUser {
  assertKeyTruthy(apiGrrUser, 'username');

  return {
    name: apiGrrUser.username,
    canaryMode: apiGrrUser.settings?.canaryMode ?? false,
    isAdmin: apiGrrUser.userType === ApiGrrUserUserType.USER_TYPE_ADMIN,
  };
}

/** Extracts usernames from API ApproverSuggestions. */
export function translateApproverSuggestions(
  suggestions: readonly ApiListApproverSuggestionsResultApproverSuggestion[],
): readonly string[] {
  return suggestions
    .map((suggestion) => suggestion.username)
    .filter((u) => u != null);
}

/** Translates an API Approval's validity into model's ApprovalStatus */
export function translateApprovalStatus(
  isValid?: boolean,
  isValidMessage?: string,
) {
  let status: ApprovalStatus;
  if (isValid) {
    status = {type: 'valid'};
  } else if (!isValidMessage) {
    throw new Error('isValidMessage attribute is missing.');
  } else if (isValidMessage.includes('Approval request is expired')) {
    status = {type: 'expired', reason: isValidMessage};
  } else if (isValidMessage.includes('Need at least')) {
    status = {type: 'pending', reason: isValidMessage};
  } else {
    status = {type: 'invalid', reason: isValidMessage};
  }
  return status;
}

/** Translates API Approval object into internal Approval model. */
export function translateApproval(
  approval: ApiHuntApproval | ApiClientApproval,
): Approval {
  assertKeyTruthy(approval, 'id');
  assertKeyTruthy(approval, 'subject');
  assertKeyTruthy(approval, 'reason');
  assertKeyTruthy(approval, 'requestor');

  const status = translateApprovalStatus(
    approval.isValid,
    approval.isValidMessage,
  );

  return {
    status,
    approvalId: approval.id,
    reason: approval.reason,
    requestedApprovers: approval.notifiedUsers ?? [],
    approvers: (approval.approvers ?? []).filter(
      (u) => u !== approval.requestor,
    ),
    requestor: approval.requestor,
    expirationTime: createOptionalDate(approval.expirationTimeUs),
  };
}
