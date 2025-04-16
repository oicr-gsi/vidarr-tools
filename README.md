# Víðarr Tools

The home of Python tools for use with Víðarr.

## Installation

vidarr-tools requires Python 3.10

1. Install pipenv

```shell
pip install --user pipenv
```

2. Install dependencies

```shell
PIPENV_VENV_IN_PROJECT=1 PIP_IGNORE_INSTALLED=1 pipenv install
```

If developing with vidarr-tools, install dev dependencies too
```shell
pipenv install --dev
```

3. To run vidarr-tools tests

```shell
pipenv run pytest
```

## Tools

### wdl2vidarr

Process WDL file and extract a Víðarr workflow definition that can be used for testing or installation.

| Argument | Required? | Description  |
|--------------------|-----------|----------------------------------------------|
| `--input-wdl-path` | True      | Source wdl path  |
| `--output-path`    | False     | Output a file with contents of the workflow parameter dict. This is just for display. |

```
wdl2vidarr -i path/to/file.wdl
```

This will output a JSON object with the workflow information.

Alternatively, the output can be written to a file

```
wdl2vidarr -i path/to/file.wdl -o path/to/output-file
```

This output can be registered in a Víðarr server:

```
wdl2vidarr -i bcl2fastq.wdl -o bcl2fastq.json
curl -X POST -d @bcl2fastq.json http://vidarr.example.com/api/workflow/bcl2fastq/1.2.3
```

This tool will automatically scan the WDL file and convert any types. However,
there are two cases where the detected type is not correct:

- the output should be sent to a data warehouse or log provisioner
- the input is for a root workflow

In both cases, extra metadata can be included in the WDL file.

```
workflow dosomething {
   ...
   meta {
     output_meta: {
       statistics: {
         vidarr_type: "warehouse"
       }
     }
  }
}
```

This will change the output type to use `"warehouse"` instead of the detected type for the workflow
output `"statistics"`. For details on the types supported,
consult [Víðarr type system information](https://oicr-gsi.github.io/vidarr/types.html).

Similarly, if the input type needs to be overridden:

```
workflow dosomething {
   ...
   parameter_meta {
     runDirectory: {
       vidarr_type: "directory"
     }
  }
}
```

In the case of most root workflows (bcl2fastq, guppy, file import), there needs
to be one entry that is associated with the input external keys. Since Cromwell
should not try to copy or link the sequencer run directory, it is desirable to
make it have the type `String` in WDL but `"directory"` in Víðarr so that
external keys can be associated with it.

Inputs can also be marked for _retry_. That allows Víðarr to try multiple values of a parameter if the workflow
failures. The allows automatically escalating the amount of memory until a job succeeds.

```
workflow dosomething {
   ...
   parameter_meta {
     memory: {
       vidarr_retry: true
     }
  }
}
```

`vidarr_type` and `vidarr_retry` can be combined. Only basic types (Booleans, dates, floats, integers, JSON, and
strings) may be retried. Input files cannot be changed by retrying.

`vidarr_label` can also be added to `output_meta` to label an output file. A label added to a WDL type `File` will upgrade it to a `Pair[File,Map[String,String]]` so that the vidarr output type will be `file-with-labels`.

```
workflow dosomething {
   ...
   output {
     File thing = something
  }
  meta {
    ...
    output_meta: {
      thing: {
        vidarr_label: "counts"
      }
    }
  }
}
```
`vidarr_type` still takes priority and no changes to `vidarr_label` will override `vidarr_type`.

### vidarr-build

vidarr-build provides configurable build, test, and deploy functionality for Víðarr workflows. Configuration files are used to specify the workflow's language and test suite. 

Currently, the following workflow languages are supported:

| Language | Processor | 
|-|-|
| WDL | [wdl2vidarr](#wdl2vidarr) |

#### vidarr-build build

Builds the workflow using the specified language's build process to produce a Víðarr-compatible workflow bundle.

| Argument | Required? | Default Value | Description |
|-|-|-|--|
| `--build-config`, `-c` | False | `vidarrbuild.json` | Specify the build file location. See [vidarrbuild.json](#vidarrbuildjson) |

vidarr-build will output the result of the specified language's processor at `v.out`. 

##### vidarrbuild.json

Configuration file which specifies the name(s) of the workflow and the workflow language. 

Expected format is as follows:

Let $LANGUAGE be one of:
- "wdl"


      {
        "names": ["myworkflow"],
        "$LANGUAGE": "myworkflow.file"
      }

vidarr-build requires that the directory containing vidarrbuild.json also contains a directory named $LANGUAGE and that directory contains the file specified in the JSON. 

#### vidarr-build test

Builds the workflow using the specified language's build process and performs regression specified by `vidarrtest-regression.json` and optionally performance tests specified by `vidarrtest-performance.json`. See [Test configuration](#test-configuration). Additionally there is an optional argument to provide an explicit output directory for those test outputs. 

| Argument             | Required? | Default Value | Description                                                                                             |
|----------------------|-|-|---------------------------------------------------------------------------------------------------------|
| `--build-config`, `-c` | False | `vidarrbuild.json` | Specify the build file location. See [vidarrbuild.json](#vidarrbuildjson)                               |
| `--test-config`, `t` | True | Environment variable `VIDARR_TEST_CONFIG` | Víðarr configuration file for running tests                                                             |
| `--performance-test`, `-p` | False | | Run performance tests specified by `vidarrtest-performance.json`                                        |
| `--output-directory`, `-o` | False | | Provide an explicit output directory for the test output files e.g. `/scratch2/groups/gsi/development/` |
| `--verbose`          | False | | Verbose mode flag helpful for debugging                                                                 |

vidarr-build will output the result of the specified language's processor and test results at `v.out`. 

##### Test configuration

`vidarrtest-regression.json` and optionally `vidarrtest-performance.json` are configuration files which specify a test suite for a workflow. The files are JSON arrays of objects which each describe one test.

Expected format is as follows:

    [
      {
        "arguments": {
          "contents": {
            "configuration": "/path/to/test/data.fastq.gz",
            "externalIds": [
              {
                "id": "TEST",
                "provider": "TEST"
              }
            ]
          },
          "type": "EXTERNAL"
        },
        "description": "Tests that workflow does its thing",
        "engineArguments": {
          "write_to_cache": false,
          "read_from_cache": false
        },
        "id": "myTest1",
        "metadata": {
          "contents": [
            {
              "outputDirectory": "/path/to/output/dir"
            }
          ],
          "type": "ALL"
          }
        },
        "validators": [
            {
            "metrics_calculate": "/path/to/calculate.sh",
            "metrics_compare": "/path/to/compare.sh",
            "output_metrics": "/path/to/output/metrics",
            "type": "script"
            }
          ]
      }
    ]

#### vidarr-build deploy

Builds the workflow using the specified language's build process and performs regression specified by `vidarrtest-regression.json` and optionally performance tests specified by `vidarrtest-performance.json`. See [Test configuration](#test-configuration). If build and test are successful, deploys built workflow to one or more remote Víðarr instances.

| Argument | Required? | Default Value | Description |
|-|-|-|--|
| `--build-config`, `-c` | False | `vidarrbuild.json` | Specify the build file location. See [vidarrbuild.json](#vidarrbuildjson) |
| `--test-config`, `t`| True | Environment variable `VIDARR_TEST_CONFIG` | Víðarr configuration file for running tests. See the [Admin Guide](https://github.com/oicr-gsi/vidarr/blob/master/admin-guide.md#creating-a-development-environment) |
| `--performance-test`, `-p` | False | | Run performance tests specified by `vidarrtest-performance.json` |
| `--url`, `-u` | False | Environment variable `VIDARR_URLS` | A Víðarr server to deploy to. If unspecified, the servers from the space-separated environment variable VIDARR_URLS will be used. |
| `--url-file`, `-U` | False | | A file containing Víðarr servers to deploy to (one per line). |
| `--version`, `-v` | True | | The version number to push as. See [Víðarr's glossary](https://github.com/oicr-gsi/vidarr/blob/master/glossary.md) |
| `--output-directory`, `-o` | False | | Provide an explicit output directory for the test output files e.g. `/scratch2/groups/gsi/development/` |
| `--verbose`          | False | | Verbose mode flag helpful for debugging                                                                 |

vidarr-build will output the result of the specified language's processor and test output at `v.out`, then push the resultant build to the Víðarr instances specified by `--url` and/or `--url-file`. 
