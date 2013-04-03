# Cron file for GRR cron jobs.

# Run every five minutes.
# Actual work is limited by grr_cron to only run as needed

*/5 * * * * root grr_cron
