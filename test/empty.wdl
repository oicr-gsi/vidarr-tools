version 1.0

workflow empty {
  input {
    File dummyInput
    Int exitCode = 0
    Int n = 10
  }
  parameter_meta {
    dummyInput: "Unused input file, strictly for Vidarr regression testing."
    exitCode: "Exit code"
    n: "Number of lines to log to stderr"
  }
  call log {
    input:
      exitCode = exitCode,
      n = n
  }
  output {
    File stdout = log.stdout
    File stderr = log.stderr
  }
  meta {
    author: "Jenniffer Meng"
    email: "jenniffer.meng@oicr.on.ca"
    description: "Workflow for testing infrastructure"
    dependencies: []
    output_meta: {
      stdout: {
                description: "stdout lines produced",
                vidarr_label: "stdout"
              },
      stderr: {
                description: "stderr lines produced",
                vidarr_label: "stderr"
              }
    }
  }
}

task log {
  input {
    Int exitCode
    Int n
    Int mem = 1
    Int runtime_seconds = 60
    Int timeout = 1
  }
  command <<<
    set -euo pipefail
    # Output n lines to stderr
    for (( i = 1; i <= ~{n}; i++ )) ; do
      echo "This is a place holder stdout line ${i}"
      echo "This is a place holder stderr line ${i}" 1>&2
    done
    sleep ~{runtime_seconds}
    exit ~{exitCode}
  >>>
  runtime {
    memory: "~{mem} GB"
    timeout: "~{timeout}"
    maxRetries: 1
  }
  output {
    File stdout = stdout()
    File stderr = stderr()
  }
  parameter_meta {
    exitCode: "Integer used to fail as appropriate"
    n: "Number of lines to log to stderr"
    mem: "Memory (in GB) to allocate to the job"
    runtime_seconds: "The amount of time (in seconds) to simulate processing/sleep for"
    timeout: "Maximum amount of time (in hours) the task can run for"
  }
  meta {
    output_meta: {
      stdout: "stdout lines produced",
      stderr: "stderr lines produced"
    }
  }
}
