# Using Terraform to deploy demo GRR setup on Google Cloud

## Installing Terraform

Please follow [these
instructions](https://www.terraform.io/intro/getting-started/install.html) to
install Terraform binary on your machine.

## Setting up a Google Cloud Project

1.  Create a new project in GCP console
    ([link](https://console.cloud.google.com/project)). Let's assume it's called
    "grr-terraform-demo".
1.  Enable billing for the project
    ([link](https://support.google.com/cloud/answer/6293499#enable-billing)).
1.  Enable Compute Engine and Cloud SQL APIs
    ([link](https://console.cloud.google.com/flows/enableapi?apiid=compute_component,sqladmin)).

## Instrumenting Terraform with credentials

1.  In Cloud Platform Console, navigate to the [Create service account
    key](https://console.cloud.google.com/apis/credentials/serviceaccountkey)
    page.
1.  From the Service account dropdown, select Compute Engine default service
    account, and leave JSON selected as the key type.
1.  Click Create, which downloads your credentials as a file named
    `[PROJECT_ID]-[UNIQUE_ID].json`.
1.  In the same shell where you're going to run Terraform (see below), run the
    following:

```bash
export GCLOUD_KEYFILE_JSON=/absolute/path/to/downloaded-file.json
```

## Running Terraform

`cd` to the folder with Terraform configuration files (and where this README
file is).

If it's the first time you run Terraform with this set of configuration files,
run:

```bash
terraform init
```

Then run (`grr-terraform-demo` is the name of a project that you've previously
set up):

```bash
terraform apply -var 'gce_project=grr-terraform-demo'
```

Run the following to get the URL of a newly deployed GRR AdminUI:

```bash
terraform output
```

Tip: you can use Terraform variables to specify the number of generated
Windows and Linux clients:

```bash
terraform apply -var 'gce_project=grr-terraform-demo' -var 'windows_client_count=4' -var 'linux_client_count=3'
```
