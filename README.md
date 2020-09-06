# Document Analyzer

## Overview
Document Analyzer is an interactive script that analyzes a set of documents and
finds the most frequent significant terms (words or stems) for those documents.

## Features

The features it supports are:

* Analyzing a set of documents & figuring out the most frequent significant terms
* Running the analysis asynchronously, using `celery` to spawn multiple jobs that
can run in parallel to decrease execution time.
* Stemming, to find the most significant stems in the set of documents
* An interactive CLI to make the process easier.

### What may be missing

Ideally, I'd also like to have included:
* unit tests
* better documentation (sphinx & autodoc)
* better output formatting (HTML & Chart.js)
* a more elegant transfer of documents to the workers (right now the content is transferred via celery's backend, in this case Redis)

## Algorithmic

To analyze the documents I decided to use `scikit-learn` `nltk`. The process roughly consists of:

* Reading the input, one document at a time
* Splitting into sentences / words (using a `CountVectorizer`)
* Optionally stemming those
* Filtering out stopwords
* Using `fit_transform` to create a sparse 2d array indicating which term of the document's vocabulary exists in which sentence.
* Using matrix operations (sum) to count term occurences
* Aggregating all results and returning the output

Regarding stopwords, initially I tried using `nltk`s builtin stopwords but they didn't seem to be good enough. For english I found a different set of stopwords on GitHub (see `stopwords.py`) which seems to be more complete and produces more meaningful results.

## Installation

### Using docker & docker-compose

To install using docker, run

```
make build
```

This will build a docker container that can be used to run both the CLI and the
worker (in case you want to analyze asynchronously).

### Local installation

To install, you can run `pip install -r requirements.py`. This will install all
required python packages for the application to run. Make sure you are using a
virtual environment to avoid messing up the system's global packages.

Developed in python 3.8.5. No other versions have been tested.

## Execution

You can check the available options anytime by running

```
python document_analyzer.py --help
```

Note that if you don't want to process asynchronously you can disregard
any steps that refer to celery & redis. In this case the `-a` option won't work.

### Datasets

Nested under `datasets/` are included 1 dataset:
* the `books` directory contains 16 english literature books that can be used as a larger dataset, ideal for asynchronous analysis.

### Using docker & docker-compose

This is the preferred way of running the script.

Using docker-compose is preferred since it's preconfigured to setup
the worker & redis correctly and make sure every component communicates
effectively with each other. Additionally, docker-compose takes care
of mounting the application's directory to the container so that you can
develop locally (and have your changes sync up with the container) and also
use input files from the host's filesystem.

First, it's best to start the required services in the background
(the worker and redis, used as a backend for celery). You can do that by running

```
docker-compose up --scale analyzer-worker=5 -d analyzer-worker
```
This will also scale the worker to 5 instances, for parallel processing.

```
docker-compose run --rm analyzer-script
```

This will open a shell in a docker container that has pre-installed
all the requirements for the script to run correctly.

Then, run the python script, e.g.

```
python document_analyzer.py -i datasets/books -s -a
```

### Local execution

To execute locally, you'll have to start a redis service.
Then, you'll have to change `analyzer/settings.py` to point to that service
and start a celery worker like so:

```
celery worker --app=analyzer --loglevel=info
```

Then, run the python script, e.g.

```
python document_analyzer.py -i datasets/books -s -a
```

If you are using `-a` and tasks aren't being consumed
or the progressbar is not being shown, then probably there's
something wrong communicating with redis. Running the script without
the `-a` option should still work.
