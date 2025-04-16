version 1.0

workflow bad {
  input {
    Int exitCode = "not an int"
  }
  call bad_task {
    input:
      exitCode = exitCode
  }
  output {
    # also not an int
    Int output_exit_code = bad_task.err
  }
}

task bad_task {
  input {
    Int exitCode
  }
  command <<<
    exit ~{exitCode}
  >>>
  output {
    File err = stderr()
  }
}