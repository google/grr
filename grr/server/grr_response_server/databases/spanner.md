# GRR on Spanner

When operating GRR you need to decide on a persistence store.

This document describes how to use [Spanner](https://cloud.google.com/spanner)
as the GRR datastore.

Spanner is a fully managed, mission-critical database service on
[Google Cloud](https://cloud.google.com) that brings together relational, graph,
key-value, and search. It offers transactional consistency at global scale,
automatic, synchronous replication for high availability.

## 1. Google Cloud Resources

Running GRR on Spanner requires that you create and configure a
[Spanner instance](https://cloud.google.com/spanner/docs/instances) before you
run GRR.

Furthermore, you also need to create a
[Google Cloud Storage](https://cloud.google.com/storage)
[Bucket](https://cloud.google.com/storage/docs/buckets) that
will serve as the GRR blobstore.

## 2. Google Cloud Spanner Instance

You can follow the instructions in the Google Cloud online documentation to
[create a Spanner instance](https://cloud.google.com/spanner/docs/create-query-database-console#create-instance).

> [!NOTE] You only need to create the
> [Spanner instance](https://cloud.google.com/spanner/docs/instances). The
> GRR [Spanner database](https://cloud.google.com/spanner/docs/databases)
> and its tables are created by running the provided [spanner_setup.sh](./spanner_setup.sh)
> script. The script assumes that you use `grr-instance` as the
> GRR instance name and `grr-database` as the GRR database name. In
> case you want to use different values then you need to update the
> [spanner_setup.sh](./spanner_setup.sh) script accordingly.
> The script assumes that you have the
> [gcloud](https://cloud.google.com/sdk/docs/install) and the
> [protoc](https://protobuf.dev/installation/) binaries installed on your machine.

Run the following command to create the GRR database and its tables:

```bash
export PROJECT_ID=<YOUR_PROJECT_ID_HERE>
export SPANNER_INSTANCE=grr-instance
export SPANNER_DATABASE=grr-database
./spanner_setup.sh
```

## 3. GRR Configuration

To run GRR on Spanner you need to configure the components settings with  
the values of the Google Cloud Spanner and the GCS Bucket resources mentioned above.

The snippet below illustrates a sample GRR `server.yaml` configuration.

```bash
    Database.implementation: SpannerDB
    Spanner.project: <YOUR_PROJECT_ID_HERE>
    Spanner.instance: grr-instance
    Spanner.database: grr-database
    Blobstore.implementation: GCSBlobStore
    Blobstore.gcs.project: <YOUR_PROJECT_ID_HERE>
    Blobstore.gcs.bucket: <YOUR_GCS_BUCKET_NAME_HERE>
```

> [!NOTE] Make sure you remove all the `Mysql` related configuration items.

## 4. IAM Permissions

This guide assumes that your GRR instance is running on the [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine) (GKE) 
and you can leverage [Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity) (WIF).

Using WIF you can assign the required IAM roles using the WIF principal
`principal://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/<PROJECT_ID.svc.id.goog/subject/ns/<K8S_NAMESPACE>/sa/<K8S_SERVICE_ACCOUNT>` 
where `K8S_NAMESPACE` is the value of the Kubernetes Namespace and `K8S_SERVICE_ACCOUNT` is the value Kubernetes Service Account that your GRR Pods are running under.

The two IAM roles that are required are:
- `roles/spanner.databaseUser` on your Spanner Database and
- `roles/storage.objectUser` on our GCS Bucket (the GRR Blobstore mentioned above).