# Data Pipeline Workshop

The aim of this workshop is to build a scalable pipeline to use to process large datasets. We'll focus on the following tasks:

- OCR (extracting text from images)
- Transcription
- Running LLM prompts on a document

As source data, we will use an Amazon S3 bucket containing:

- podcasts/ - a selection of recent episodes from podcasts from a few different european countries
- company_reports/ - company reports of the FTSE 350 companies from the london stock exchange

The workshop has three parts:

1.  Creating the cloud infrastructure we will use for the project (`infrastructure/`)

- A queue, which we'll use to schedule jobs for our workers
- A worker pool - computers to perform the OCR/Transcription/LLM operations. Known as an 'auto scaling group' in AWS.

2.  Scheduling some work. See `populator/`.
3.  Running the desired task on the work we have scheduled. See `worker/`.

## Setup

For this workshop, you will need access to AWS. Go to https://708599814125.signin.aws.amazon.com/console/?region=eu-west-1
and login using the credentials provided. Once you have logged in, in a terminal window run the command:

```bash
aws login --profile dataharvest --region eu-west-1
```

It should pop open a browser. Select the account you just signed into.

To test that your credentials are working, run `aws s3 ls --profile dataharvest` - you should see a list of data harvest related S3 buckets.

## Creating your pipeline

To manage the cloud infrastructure we'll need for this workshop, we're using some software called Open Tofu. This allows us to
define all the things we need in a single file, rather than having to click lots of buttons in the cloud console. To begin with,make sure you have installed open tofu by following the instructions here: https://opentofu.org/docs/intro/install/.

Once opentofu is installed, we need to initialise the opentofu project we'll be using. Run `tofu init` inside the `infrastructure`
directory:

```
cd infrastructure/
tofu init
```

Next, take a look at `infrastructure/workers.tf` - this is the OpenTofu file that defines the infrastructure we'll need for the pipeline. There isn't time to learn the details of OpenTofu now, but you could read through the comments of the file to get an idea of what will be created in AWS.

Change the projectName variable inside the `infrastructure/workers.tf` file file from 'phil-test' to something else. This ensures that you'll be able to tell apart cloud resources you've created from others doing the workshop.

Once you have changed the project name, run `tofu apply` to create your infrastructure. OpenTofu will show a list of all the things it
will do, type 'yes' to tell it to go ahead.

Once OpenTofu has finished creating your infrastructure, you can go check it's there in the console:

- SQS console:
- S3 console:
- Autoscaling group console:

## Scheduling some work

Now we've got our infrastructure, we need to put some messages on the queue containing the work we want done.

Take a look at the contents of the source data S3 bucket and decide which files you want to work on. Initially it's best to pick something out of the `short_files` directory. Once you have identified a directory, note down the path to the files, e.g. `short_files/beatles_samples`

Next, take a look at the `populator/` subdirectory. This contains the script we'll use to add messages to the queue. The basic behaviour
of the script is:

- List files in the S3 bucket
- Add a reference to the file, together with a jobType and any extra necessay data to the queue.

Whilst it's possible to write some code to auto detect the type of file and process it accordingly, to keep things simple we'll be
telling the populator what job we want to run on the input files. Initially, we'll start with transcription and ocr.

To run the populator you need a program called `uv` installed. Follow the instructions here https://docs.astral.sh/uv/getting-started/installation/ to install it.

Once you have uv installed, run `uv sync` to install the dependencies needed by the populator script:

```bash
cd data-pipeline/
uv sync
```

Now we can run the populator script:

```bash
uv run queue-populator [QUEUE_URL] [PATH] [JOB_TYPE]
```

You'll need to replace the arguments:

- QUEUE_URL: Fetch it from the SQS console
- PATH: path to the files in S3 you want to process
- JOB_TYPE: either 'transcribe' or 'ocr'

## Running the workers and checking the output

Now we have some work in the queue, we need to start a worker. Go to the autoscaling console, find your worker autoscaling group
and set the desired number of instances to 1. If you go to the 'instance management' tab you should see a new instance starting up.

The worker has been pre-configured to install any necessary dependencies and start processing the queue. To see how it's getting on,
we need to look at the output logs from the service. There are two ways of doing this, initially we'll just login to the machine using the AWS console.

(Note that if you're using another cloud provider or don't want to lock in to AWS you can use SSH for this step, AWS tools are just easier in the workshop context)

### Using AWS console

Find your instance by going to the autoscaling group console, finding your autoscaling group, selecting the 'instance management' tab
and then clicking on the instance id of your instance. This will open in a new tab. Click 'connect' and then on the next page 'connect'
again.

Once you are logged in, there are two files of interest. `/var/log/cloud-init-output.log` will show you everything that happened when the instance started up. At the end of the startup process it starts the worker. From then on, logs will appear in
`/opt/dlami/nvme/worker.log`.

To see what's in these files, you can use `tail -f` to follow along whilst stuff is happening:

```bash
tail -f /var/log/cloud-init-output.log
tail -f /opt/dlami/nvme/worker.log
```

Or you can use `cat` to dump the whole file to the screen:

```bash
cat /var/log/cloud-init-output.log
cat /opt/dlami/nvme/worker.log
```

`worker.log` contains all the output from the worker.py script. You can either `cat worker.log` to dump everything to the terminal, or run `tail -f worker.log` to follow along as it processes the files.

If you'd prefer to use your own terminal rather than the browser then you can install the AWS CLI session manager plugin from
[here](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) and then login
using the instance id:

```bash
aws ssm start-session --profile workshop --target <id>
sudo su ubuntu
cd /home/ubuntu
```

## Analysing the output using an LLM

Hopefully by this point you have some data in your output bucket. The next step is to feed this output into an LLM to do some analysis.

Firstly, let's purge the queue of any leftover work. You can do this in the SQS console.

Next, edit `prompts/system_prompt.txt` to contain a description of the type of data you are looking for. See `example_prompt.txt` for insipration.

Now, run the populator with your prompt along and the location of the output files. Note that this time you'll need to tell the populator to read from your output bucket

```bash
uv run queue-populator [QUEUE_URL] [PATH] prompt --bucket [OUTPUT_BUCKET] --system-prompt-file `prompts/system_prompt.txt`
```

It's worth logging onto the machine again to check it's doing as you expect. Eventually you should start seeing files appear
in the S3 console at the PATH you provided. You should be able to download and take a look at the files.

## Gathering output into a single file

It would be easier to look at the output data if we had it all in one place. There is a script 'collector' provided which will
download all the output prompt files and combine them into a single CSV (spreadsheet) file. You can run it like this:

```
uv run collector [OUTPUT_BUCKET] prompt/
```
