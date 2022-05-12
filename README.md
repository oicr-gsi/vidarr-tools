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
pipenv install
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

| Argument           | Required? | Description                                                                           |
|--------------------|-----------|---------------------------------------------------------------------------------------|
| `--input-wdl-path` | True      | Source wdl path                                                                       |
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
make it have the type `String` in WDL but `"directory"` in Vidarr so that
external keys can be associated with it.
