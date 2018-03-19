$env:PATH += ';C:\grr_deps\google-cloud-sdk\bin'

gcloud auth activate-service-account --key-file C:\grr_src\appveyor\appveyor_uploader_service_account.json

if (!$?) {
  exit 1
}

# Parse appveyor IS0 8601 commit date string (e.g 2017-07-26T16:49:31.0000000Z)
# into a Powershell DateTime object
$raw_commit_dt = [DateTime]$env:APPVEYOR_REPO_COMMIT_TIMESTAMP

# Create a shorter, more readable time string.
$short_commit_timestamp = $raw_commit_dt.ToString('yyyy-MM-ddTHH:mmUTC')

$gcs_dest = 'gs://{0}/{1}_{2}/appveyor_build_{3}_job_{4}/' -f @(
    $env:GCS_BUCKET,
    $short_commit_timestamp,
    $env:APPVEYOR_REPO_COMMIT,
    $env:APPVEYOR_BUILD_NUMBER,
    $env:APPVEYOR_JOB_NUMBER)

Write-Output "Uploading templates to $gcs_dest"

$stop_watch = [Diagnostics.Stopwatch]::StartNew()
gsutil cp 'C:\grr_src\output\*' $gcs_dest
if (!$?) {
  exit 2
}
$stop_watch.Stop()
$upload_duration = $stop_watch.Elapsed.TotalSeconds

# gsutil will print an info message recommending using the -m option (parallel
# object upload) when copying objects to GCP. For some reason however, that
# doesn't seem to work properly on Appveyor. Some files arbitrarily fail to
# upload with unhelpful error messages like 'Duplicate type [0:0:2]'
Write-Output "Sequential object upload took $upload_duration seconds"
