#!/usr/bin/env python
"""This tests the performance of the AFF4 subsystem."""



from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import test_lib


class AFF4Benchmark(test_lib.AverageMicroBenchmarks):
  """Test performance of the AFF4 subsystem."""

  REPEATS = 50

  def testAFF4Creation(self):
    """How fast can we create new AFF4 objects."""

    def CreateAFF4Object(object_type="AFF4Object", urn="aff4:/test"):
      fd = aff4.FACTORY.Create(urn, object_type, token=self.token)
      fd.Close()

    for object_type in ["AFF4Object", "HashImage", "AFF4MemoryStream"]:
      self.TimeIt(CreateAFF4Object, name="Create %s" % object_type,
                  object_type=object_type)

    self.TimeIt(CreateAFF4Object, name="Create VFSGRRClient",
                object_type="VFSGRRClient", urn="C.1234567812345678")

  def testAFF4CreateAndSet(self):
    """How long does it take to create and set properties."""

    client_info = rdfvalue.ClientInformation(client_name="GRR",
                                             client_description="Description")

    def CreateAFF4Object():
      """Blind write a VFSGRRClient with 1000 client info attributes."""
      fd = aff4.FACTORY.Create("C.1234567812345678", "VFSGRRClient",
                               token=self.token)
      fd.Set(fd.Schema.HOSTNAME("Foobar"))
      for _ in range(1000):
        fd.AddAttribute(fd.Schema.CLIENT_INFO, client_info)

      fd.Close()

    # Time creation  into an empty data store.
    self.TimeIt(CreateAFF4Object, pre=data_store.DB.Clear)

    # Now we want to measure the time to read one of these object.
    data_store.DB.Clear()
    CreateAFF4Object()

    def ReadAFF4Object():
      fd = aff4.FACTORY.Open("C.1234567812345678", token=self.token,
                             ignore_cache=True, age=aff4.ALL_TIMES)
      self.assertEqual(fd.Get(fd.Schema.HOSTNAME), "Foobar")

    self.TimeIt(ReadAFF4Object, name="Read attribute from AFF4Object")

    def ReadVersionedAFF4Attribute():
      fd = aff4.FACTORY.Open("C.1234567812345678", token=self.token,
                             ignore_cache=True, age=aff4.ALL_TIMES)
      for x in fd.GetValuesForAttribute(fd.Schema.CLIENT_INFO):
        self.assertEqual(x.client_name, "GRR")

    self.TimeIt(ReadVersionedAFF4Attribute,
                name="Read heavily versioned Attributes")

    def ReadSomeVersionedAFF4Attribute():
      fd = aff4.FACTORY.Open("C.1234567812345678", token=self.token,
                             ignore_cache=True, age=aff4.ALL_TIMES)

      # Only read the top 5 attributes.
      for i, x in enumerate(fd.GetValuesForAttribute(fd.Schema.CLIENT_INFO)):
        self.assertEqual(x.client_name, "GRR")
        if i > 50:
          break

    self.TimeIt(ReadSomeVersionedAFF4Attribute,
                name="Read few versioned Attributes")

    # Using Get() on a multi versioned object should only parse one value.
    def ReadAVersionedAFF4Attribute():
      fd = aff4.FACTORY.Open("C.1234567812345678", token=self.token,
                             ignore_cache=True, age=aff4.ALL_TIMES)

      x = fd.Get(fd.Schema.CLIENT_INFO)
      self.assertEqual(x.client_name, "GRR")

    self.TimeIt(ReadAVersionedAFF4Attribute,
                name="Read one versioned Attributes")
