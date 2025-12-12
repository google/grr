#!/usr/bin/env python
"""Configuration parameters for the admin UI."""

from grr_response_core.lib import config_lib
from grr_response_core.lib.rdfvalues import config as rdf_config

# The Admin UI web application.
config_lib.DEFINE_integer("AdminUI.port", 8000, "port to listen on")

config_lib.DEFINE_integer(
    "AdminUI.port_max",
    None,
    "If set and AdminUI.port is in use, attempt to "
    "use ports between AdminUI.port and "
    "AdminUI.port_max.",
)

# Override this if you want to access admin ui extenally. Make sure it is
# secured (i.e. AdminUI.webauth_manager is not NullWebAuthManager)!
config_lib.DEFINE_string("AdminUI.bind", "127.0.0.1", "interface to bind to.")

config_lib.DEFINE_string(
    "AdminUI.document_root",
    "%(grr_response_server/gui/static@grr-response-server|resource)",
    "The main path to the static HTML pages.",
)

config_lib.DEFINE_string(
    "AdminUI.template_root",
    "%(grr_response_server/gui/templates@grr-response-server|resource)",
    "The main path to the templates.",
)

config_lib.DEFINE_string(
    "AdminUI.css_font_override",
    "",
    "The main path to the fonts CSS files.",
)

config_lib.DEFINE_string(
    "AdminUI.webauth_manager",
    "NullWebAuthManager",
    "The web auth manager for controlling access to the UI.",
)

config_lib.DEFINE_string(
    "AdminUI.remote_user_header",
    "X-Remote-User",
    "Header containing authenticated user's username. "
    "Used by RemoteUserWebAuthManager.",
)
config_lib.DEFINE_string(
    "AdminUI.remote_email_header",
    "X-Remote-Extra-Email",
    "Header containing authenticated user's e-mail address. "
    "If present, the e-mail address of a newly created GRR user will be set "
    "to the header's value. "
    "Used by RemoteUserWebAuthManager.",
)
config_lib.DEFINE_list(
    "AdminUI.remote_user_trusted_ips",
    ["127.0.0.1"],
    "Only requests coming from these IPs will be processed "
    "by RemoteUserWebAuthManager.",
)

config_lib.DEFINE_string(
    "AdminUI.firebase_api_key",
    None,
    "Firebase API key. Used by FirebaseWebAuthManager.",
)
config_lib.DEFINE_string(
    "AdminUI.firebase_auth_domain",
    None,
    "Firebase API key. Used by FirebaseWebAuthManager.",
)
config_lib.DEFINE_string(
    "AdminUI.firebase_auth_provider",
    "GoogleAuthProvider",
    "Firebase auth provider (see "
    "https://firebase.google.com/docs/auth/web/start). Used by "
    "FirebaseWebAuthManager.",
)

config_lib.DEFINE_string(
    "AdminUI.csrf_secret_key",
    "CHANGE_ME",
    "This is a secret key that should be set in the server "
    "config. It is used in CSRF protection.",
)

config_lib.DEFINE_string(
    "AdminUI.csrf_token_generator",
    "RawKeyCSRFTokenGenerator",
    "The class name of the CSRF token generator to use.",
)

config_lib.DEFINE_bool(
    "AdminUI.enable_ssl",
    False,
    "Turn on SSL. This needs AdminUI.ssl_cert to be set.",
)

config_lib.DEFINE_string(
    "AdminUI.ssl_cert_file", "", "The SSL certificate to use."
)

config_lib.DEFINE_string(
    "AdminUI.ssl_key_file",
    None,
    "The SSL key to use. The key may also be part of the cert file, in which "
    "case this can be omitted.",
)

config_lib.DEFINE_string(
    "AdminUI.url",
    "http://localhost:8000/",
    "The direct external URL for the user interface.",
)

config_lib.DEFINE_bool(
    "AdminUI.use_precompiled_js",
    False,
    "If True - use Closure-compiled JS bundle. This flag "
    "is experimental and is not properly supported yet.",
)

config_lib.DEFINE_string(
    "AdminUI.export_command",
    "/usr/bin/grr_api_shell '%(AdminUI.url)'",
    "Command to show in the fileview for downloading the "
    "files from the command line.",
)

config_lib.DEFINE_string(
    "AdminUI.heading", "", "Dashboard heading displayed in the Admin UI."
)

config_lib.DEFINE_string(
    "AdminUI.report_url",
    "https://github.com/google/grr/issues",
    "URL of the 'Report a problem' link.",
)

config_lib.DEFINE_string(
    "AdminUI.help_url", "/help/index.html", "URL of the 'Help' link."
)

config_lib.DEFINE_string(
    "AdminUI.docs_location",
    "https://grr-doc.readthedocs.io/en/v%(Source.version_major)."
    "%(Source.version_minor).%(Source.version_revision)",
    "Base path for GRR documentation. ",
)


# This accepts a comma-separated list of multiple plugins. Ideally, we'd use
# DEFINE_list instead of DEFINE_string, but returning lists as values of the
# config options is not supported by the GRR API (see  ApiDataObjectKeyValuePair
# class and proto).
config_lib.DEFINE_string(
    "AdminUI.new_hunt_wizard.default_output_plugins",
    None,
    "Output plugin(s) that will be added by default in the "
    "'New Hunt' wizard output plugins selection page. Accepts comma-separated "
    "list of multiple plugins.",
)

# This accepts a comma-separated list of multiple plugins.
config_lib.DEFINE_string(
    "AdminUI.new_flow_form.default_output_plugins",
    None,
    "Output plugin(s) that will be added by default in the "
    "'Start Flow' form output plugins section. Accepts comma-separated "
    "list of multiple plugins.",
)

config_lib.DEFINE_semantic_struct(
    rdf_config.AdminUIHuntConfig,
    "AdminUI.hunt_config",
    None,
    "List of labels to include or exclude by default when hunts are created,"
    " and warning message to be shown.",
)

config_lib.DEFINE_semantic_struct(
    rdf_config.AdminUIClientWarningsConfigOption,
    "AdminUI.client_warnings",
    None,
    "List of per-client-label warning messages to be shown.",
)

config_lib.DEFINE_string(
    "AdminUI.analytics_id",
    None,
    "The Google Analytics ID to use for logging interactions when users access "
    "the web UI. If None (default), no Analytics script will be included and "
    "no events will be logged.",
)

config_lib.DEFINE_bool(
    "AdminUI.rapid_hunts_enabled",
    True,
    "If True, enabled 'rapid hunts' feature in the Hunts Wizard. Rapid hunts "
    "support will automatically set client rate to 0 in FileFinder hunts "
    "matching certain criteria (no recursive globs, no file downloads, etc).",
)

config_lib.DEFINE_string(
    "AdminUI.debug_impersonate_user",
    None,
    "NOTE: for debugging purposes only! If set, every request AdminUI gets "
    "will be attributed to the specified user. Useful for checking how AdminUI "
    "looks like for an access-restricted user.",
)

config_lib.DEFINE_bool(
    "AdminUI.headless",
    False,
    "When running in headless mode, AdminUI ignores checks for JS/CSS compiled "
    "bundles being present. AdminUI.headless=True should be used to run "
    "the AdminUI as an API endpoint only.",
)

# Configuration requirements for Cloud IAP Setup.
config_lib.DEFINE_string(
    "AdminUI.google_cloud_project_id",
    None,
    "Cloud Project ID for IAP. This must be set if "
    "the IAPWebAuthManager is used.",
)

config_lib.DEFINE_string(
    "AdminUI.google_cloud_backend_service_id",
    None,
    "GCP Cloud Backend Service ID for IAP. This must be set if "
    "the IAPWebAuthManager is used.",
)

config_lib.DEFINE_string(
    "AdminUI.profile_image_url",
    None,
    "URL to user's profile images. The placeholder {username} is replaced with "
    "the actual value. E.g. https://avatars.example.com/{username}.jpg",
)

config_lib.DEFINE_bool(
    "AdminUI.csp_enabled",
    False,
    "If True, enable the Content Security Policy header.",
)

config_lib.DEFINE_string(
    "AdminUI.csp_policy",
    "{}",
    "A JSON string of keys to lists of values to include in the Content "
    'Security Policy header. E.g. {"default-src": ["https:"]}',
)

config_lib.DEFINE_bool(
    "AdminUI.csp_report_only",
    True,
    "If True, set the Content Security Policy header to 'report only' mode. "
    "This flag has no effect if AdminUI.csp_enabled is False.",
)

config_lib.DEFINE_bool(
    "AdminUI.trusted_types_enabled",
    True,
    "If True, enable the Trusted Types feature of the Content Security Policy "
    "header. Combined with setting 'AdminUI.trusted_types_report_only' to "
    "True, this setting will have no effect on the behavior of GRR - it will "
    "only report Trusted Types violations in your browser developer console. "
    "Trusted Types can prevent most common XSS attacks, see "
    "https://web.dev/trusted-types/ for more information.",
)

config_lib.DEFINE_bool(
    "AdminUI.trusted_types_report_only",
    True,
    "If True, set the Trusted Types Content Security Policy header to 'report "
    "only' mode. When in 'report only' mode, Trusted Types violations will be "
    "logged to the browser developer console, but the behavior of GRR will "
    "not change. When this flag is set to False, Trusted Types rules will be "
    "enforced. This flag has no effect if AdminUI.trusted_types_enabled is "
    "False. See https://web.dev/trusted-types/ for more information.",
)

config_lib.DEFINE_string(
    "AdminUI.csp_report_uri",
    None,
    "URL to report Content Security Policy violations to.",
)

config_lib.DEFINE_list(
    "AdminUI.csp_include_url_prefixes",
    ["/v2"],
    "Only requests for URLs with these prefixes will have a Content Security "
    "Policy header added. Leave empty to include all URLs.",
)

config_lib.DEFINE_list(
    "AdminUI.csp_exclude_url_prefixes",
    [],
    "Requests for URLs with these prefixes will not have a Content Security "
    "Policy header added. This is applied to URLs after applying "
    "AdminUI.csp_include_url_prefixes.",
)
