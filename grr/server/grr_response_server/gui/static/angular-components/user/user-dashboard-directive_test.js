goog.module('grrUi.user.userDashboardDirectiveTest');
goog.setTestOnly();

const {filterOutDuplicateApprovals} = goog.require('grrUi.user.userDashboardDirective');

describe('userDashboardDirective.filterOutDuplicateApprovals', () => {
  let index = 0;
  function approval(clientId, isValid) {
    index += 1;
    return {
      value: {
        is_valid: {
          value: isValid,
        },
        id: {
          value: index,
        },
        subject: {
          value: {
            client_id: {value: clientId,},
          },
        }
      }
    };
  }

  it('does not remove any of 2 invalid approvals for different subjects', () => {
    const approvals = [
      approval('C.0', false),
      approval('C.1', false),
    ];
    const filteredApprovals = filterOutDuplicateApprovals(approvals);

    expect(filteredApprovals).toEqual(approvals);
  });

  it('prefers later invalid approval for the same client', () => {
    // As approvals are expected to be sorted in reversed-timestamp order,
    // "later" means the one that appears earlier in the list.
    const approvals = [
      approval('C.0', false),
      approval('C.0', false),
      approval('C.0', false),
    ];
    const filteredApprovals = filterOutDuplicateApprovals(approvals);

    expect(filteredApprovals).toEqual([approvals[0]]);
  });

  it('prefers later valid approval for the same client', () => {
    // As approvals are expected to be sorted in reversed-timestamp order,
    // "later" means the one that appears earlier in the list.
    const approvals = [
      approval('C.0', true),
      approval('C.0', true),
      approval('C.0', true),
    ];
    const filteredApprovals = filterOutDuplicateApprovals(approvals);

    expect(filteredApprovals).toEqual([approvals[0]]);
  });

  it('removes invalid approval if valid is present', () => {
    const approvals = [
      approval('C.0', true),
      approval('C.0', false),
    ];
    const filteredApprovals = filterOutDuplicateApprovals(approvals);

    expect(filteredApprovals).toEqual([approvals[0]]);
  });

  it('removes multiple invalid approvals if valid is present', () => {
    const approvals = [
      approval('C.0', false),
      approval('C.0', false),
      approval('C.0', true),
      approval('C.0', false),
      approval('C.0', false),
    ];
    const filteredApprovals = filterOutDuplicateApprovals(approvals);

    expect(filteredApprovals).toEqual([approvals[2]]);
  });

  it('removes multiple invalid approvals for multiple clients', () => {
    const approvals = [
      approval('C.0', false),
      approval('C.0', true),
      approval('C.0', false),
      approval('C.1', false),
      approval('C.1', true),
      approval('C.1', false),
    ];
    const filteredApprovals = filterOutDuplicateApprovals(approvals);

    expect(filteredApprovals).toEqual([approvals[1], approvals[4]]);
  });
});
