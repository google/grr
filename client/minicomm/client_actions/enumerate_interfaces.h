#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_INTERFACES_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_INTERFACES_H_

#include <ifaddrs.h>

#include <map>

#include "gtest/gtest_prod.h"
#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {

class EnumerateInterfaces : public ClientAction {
 public:
  void ProcessRequest(ActionContext* args) override;

 private:
  // Map from interface name to interface information.
  typedef std::map<std::string, Interface> InterfaceMap;

  // Process a linked list of addresses, as returned by the getifaddrs system
  // call.
  InterfaceMap ProcessIfaddrList(const struct ifaddrs* addresses);

  FRIEND_TEST(EnumerateInterfacesTest, ProcessIfaddrList);
};
}  // namespace actions
}  // namespace grr
#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_INTERFACES_H_
