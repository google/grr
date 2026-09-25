#!/usr/bin/env python
from absl.testing import absltest

from grr_response_server import flow_responses
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


class ResponsesTest(absltest.TestCase):

  def testFromResponsesProto2AnyDuplicatedStatus(self):
    status_response_1 = rdf_flow_objects.FlowStatus()
    status_response_1.status = rdf_flow_objects.FlowStatus.Status.OK  # pyrefly: ignore[missing-attribute]

    status_response_2 = rdf_flow_objects.FlowStatus()
    status_response_2.status = rdf_flow_objects.FlowStatus.Status.OK  # pyrefly: ignore[missing-attribute]

    responses = [
        status_response_1,
        status_response_2,
    ]

    with self.assertRaisesRegex(ValueError, "Duplicated status"):
      flow_responses.Responses.FromResponsesProto2Any(responses)

  def testFromResponsesProto2AnyMissingStatus(self):
    response_1 = rdf_flow_objects.FlowResponse()
    response_1.any_payload.value = b"foo"  # pyrefly: ignore[missing-attribute]

    response_2 = rdf_flow_objects.FlowResponse()
    response_2.any_payload.value = b"bar"  # pyrefly: ignore[missing-attribute]

    responses = [
        response_1,
        response_2,
    ]

    with self.assertRaisesRegex(ValueError, "Missing status"):
      flow_responses.Responses.FromResponsesProto2Any(responses)

  def testFromResponsesProto2AnyUnexpectedResponse(self):
    response_1 = rdf_flow_objects.FlowResponse()
    response_1.any_payload.value = b"foo"  # pyrefly: ignore[missing-attribute]

    response_2 = rdf_flow_objects.FlowResponse()
    response_2.any_payload.value = b"bar"  # pyrefly: ignore[missing-attribute]

    # An unsupported response type should trigger the exception.
    unsupported_response = "unsupported_response"

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK  # pyrefly: ignore[missing-attribute]

    responses = [
        response_1,
        response_2,
        unsupported_response,
        status_response,
    ]

    with self.assertRaisesRegex(TypeError, "Unexpected response"):
      flow_responses.Responses.FromResponsesProto2Any(responses)  # pyrefly: ignore[bad-argument-type]

  def testFromResponsesProto2AnyOK(self):
    response_1 = rdf_flow_objects.FlowResponse()
    response_1.any_payload.value = b"foo"  # pyrefly: ignore[missing-attribute]

    response_2 = rdf_flow_objects.FlowResponse()
    response_2.any_payload.value = b"bar"  # pyrefly: ignore[missing-attribute]

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK  # pyrefly: ignore[missing-attribute]

    responses = [
        response_1,
        response_2,
        status_response,
    ]

    responses = flow_responses.Responses.FromResponsesProto2Any(responses)
    self.assertLen(responses, 2)
    self.assertEqual(responses.status, status_response)
    self.assertEqual(list(responses)[0].value, b"foo")
    self.assertEqual(list(responses)[1].value, b"bar")

  def testFromResponsesProto2AnyAddsRequest(self):
    request = rdf_flow_objects.FlowRequest()
    request.client_id = "C.123456"  # pyrefly: ignore[missing-attribute]
    request.flow_id = "F123456"  # pyrefly: ignore[missing-attribute]
    request.request_id = 1  # pyrefly: ignore[missing-attribute]
    request.request_data = {"foo": "bar"}  # pyrefly: ignore[missing-attribute]

    # This is required, otherwise the method raises.
    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK  # pyrefly: ignore[missing-attribute]
    responses = [
        status_response,
    ]

    responses = flow_responses.Responses.FromResponsesProto2Any(
        responses, request
    )
    self.assertEqual(responses.request, request)
    self.assertEqual(responses.request_data, request.request_data)  # pyrefly: ignore[missing-attribute]


if __name__ == "__main__":
  absltest.main()
