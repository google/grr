# Visibility:  please choose a more appropriate default for the package,
# and update any rules that should be different.
# See: http://goto/package-visibility
package(default_visibility = ["//visibility:legacy_public"])

py_binary(
    name = "data_server",
    srcs = [
        "__init__.py",
        "data_server.py",
        "master.py",
        "rebalance.py",
        "store.py",
    ],
    data = [
        "//grr/config:configs",
    ],
    deps = [
        ":data_server_lib",
        ":master_lib",
        "//grr/lib:server_lib",
        "//grr/lib/data_stores:libdata_store",
        "// py/requests",
    ],
)

py_binary(
    name = "manager",
    srcs = [
        "__init__.py",
        "manager.py",
        "rebalance.py",
    ],
    deps = [
        ":data_server_lib",
        "// py/requests",
    ],
)

py_library(
    name = "data_server_lib",
    srcs = [
        "auth.py",
        "constants.py",
        "errors.py",
        "utils.py",
    ],
    deps = [
        "//grr/lib:common_lib",
        "//grr/lib:rdfvalue_lib",
        "//grr/proto:data_server_proto",
        "//grr/proto:data_store_proto",
    ],
)

py_library(
    name = "master_lib",
    srcs = [
        "master.py",
        "rebalance.py",
        "store.py",
    ],
    deps = [
        ":data_server_lib",
        "//grr/lib:common_lib",
        "//grr/proto:data_server_proto",
        "// py/requests",
    ],
)

py_test(
    name = "auth_test",
    size = "small",
    srcs = ["auth_test.py"],
    deps = [
        ":data_server_lib",
        "//grr/lib:test_lib",
    ],
)

py_test(
    name = "master_test",
    size = "small",
    srcs = ["master_test.py"],
    deps = [
        ":master_lib",
        "//grr/lib:test_lib",
    ],
)
