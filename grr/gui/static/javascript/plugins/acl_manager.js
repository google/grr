var grr = window.grr || {};

grr.Renderer('ACLDialog', {
  Layout: function(state) {
    $('#acl_dialog_submit').click(function(event) {
      $('#acl_form form').submit();
    });

    grr.subscribe('unauthorized', function(subject, message) {
      if (subject) {
        var grrAclDialogService =
            grr.angularInjector.get('grrAclDialogService');

        // TODO(user): get rid of this code as soon as we stop passing
        // information about objects by passing URNs and guessing the
        // object type.
        subject = subject.replace(/^aff4:\//, '');
        var components = subject.split('/');
        if (/^C\.[0-9a-fA-F]{16}$/.test(components[0])) {
          grrAclDialogService.openRequestClientApprovalDialog(
              components[0], message);
        } else if (components[0] == 'hunts') {
          grrAclDialogService.openRequestHuntApprovalDialog(
              components[1], message);
        } else if (components[0] == 'cron') {
          grrAclDialogService.openRequestCronJobApprovalDialog(
              components[1], message);
        } else {
          throw new Error('Can\'t determine type of resources.');
        }
      }
    }, 'acl_dialog');
  }
});
