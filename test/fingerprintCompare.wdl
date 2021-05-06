version 1.0

workflow fingerprintCompare {

    input {
        Array[File] inputs
    }

    call generateFinList { input: inputs = inputs}
    call generateMatrix { input: finList = generateFinList.finList }

    parameter_meta {
        inputs: "A list of FIN files generated from fingerprintCollector workflow"
    }

    meta {
        author: "Michelle Feng"
        email: "mfeng@oicr.on.ca"
        description: "Workflow to generate jaccard matrices for all projects."
        dependencies: [
            {
            name: "perl/5.30",
            url: "https://www.perl.org/"
            }
        ]
        output_meta: {
            jaccardMatrix: "A matrix of jaccard scores from pairwise comparisions between the fingerprints."
        }
    }

    output {
        File jaccardMatrix = generateMatrix.jaccardMatrix
    }
}

task generateFinList {

    input {
        Array[File] inputs
        Int timeout = 5
        Int memory = 20
    }

    parameter_meta {
        inputs: "A list of FIN files generated from fingerprintCollector"
        timeout: "Timeout in hours, needed to override imposed limits"
        memory: "Memory allocated for job"
    }

    command <<<
        mkdir finFiles
        while read line ; do
            ln -s $line finFiles/$(basename $line)
        done < ~{write_lines(inputs)}
        echo $PWD/finFiles
    >>>

    runtime {
        timeout: "~{timeout}"
        memory: "~{memory}G"
    }

    output {
        File finList = write_lines(inputs)
    }

    meta {
        output_meta: {
            finList: "Input file for generateMatrix containing list of .fin files"
        }
    }
}

task generateMatrix {

    input {
        File finList
        String modules = "sample-fingerprinting/0"
        Int timeout = 5
        Int memory = 20
    }

    parameter_meta {
        finList: "The .txt file containing a list of .fin files on which a jaccard matrix will be generated."
        modules: "Names and versions of modules."
        timeout: "Timeout in hours, needed to override imposed limits."
        memory: "Memory allocated for job."
    }

    command <<<
        jaccard_coeff_matrix_mc --list ~{finList} > matrix.txt
    >>>

    runtime {
        modules: "~{modules}"
        timeout: "~{timeout}"
        memory: "~{memory}G"
    }

    output {
        File jaccardMatrix = "matrix.txt"
    }

    meta {
        output_meta: {
            jaccardMatrix: "A matrix of jaccard scores from pairwise comparisions between the fingerprints."
        }
    }
}
