version 1.0
workflow crosscheckFingerprints {
    input {
        Array[File] inputs
        String haplotypeMapFileName
        String haplotypeMapDir = "$CROSSCHECKFINGERPRINTS_HAPLOTYPE_MAP_ROOT"
        String outputPrefix = "output"
    }
    String haplotypeMap = "~{haplotypeMapDir}/~{haplotypeMapFileName}"

    parameter_meta {
        inputs: "A list of SAM/BAM/VCF files to fingerprint."
        haplotypeMapFileName: "The file name that lists a set of SNPs, optionally arranged in high-LD blocks, to be used for fingerprinting."
        haplotypeMapDir: "The directory that contains haplotype map files. By default the modulator data directory."
        outputPrefix: "Text to prepend to all output."
    }

    meta {
        author: "Savo Lazic"
        email: "savo.lazic@oicr.on.ca"
        description: "Checks if all the genetic data within a set of files appear to come from the same individual by using Picard [CrosscheckFingerprints](https://gatk.broadinstitute.org/hc/en-us/articles/360037594711-CrosscheckFingerprints-Picard-)"
        dependencies:
        [
            {
                name: "picard/3.1.0",
                url: "https://github.com/broadinstitute/picard/releases/tag/3.1.0"
            },
            {
                name: "crosscheckfingerprints-haplotype-map/20230324",
                url: "https://github.com/oicr-gsi/fingerprint_maps"
            }
        ]
    output_meta: {
    crosscheckMetrics: {
        description: "The crosschecksMetrics file produced by Picard CrosscheckFingerprints",
        vidarr_label: "crosscheckMetrics"
    },
    crosscheckMetricsMatrix: {
        description: "Matrix of LOD scores. This is less informative than the metrics output and only contains Normal-Normal LOD score (i.e. doesn't account for Loss of Heterozygosity.",
        vidarr_label: "crosscheckMetricsMatrix"
    }
}
    }


    call runCrosscheckFingerprints {
        input:
            inputs = inputs,
            haplotypeMap = haplotypeMap,
            outputPrefix = outputPrefix
    }

    output {
        File crosscheckMetrics = runCrosscheckFingerprints.crosscheckMetrics
        File crosscheckMetricsMatrix = runCrosscheckFingerprints.crosscheckMetricsMatrix
    }
}

task runCrosscheckFingerprints {
    input {
        Array[File] inputs
        String haplotypeMap
        String outputPrefix
        String crosscheckBy = "READGROUP"
        Int picardMaxMemMb = 3000
        Int exitCodeWhenMismatch = 0
        Int exitCodeWhenNoValidChecks = 0
        Float lodThreshold = 0.0
        String validationStringency = "SILENT"
        String modules = "picard/3.1.0 crosscheckfingerprints-haplotype-map/20230324"
        Int threads = 4
        Int jobMemory = 6
        Int timeout = 6
    }
    Array[String] inputCommand = prefix("INPUT=", inputs)

    parameter_meta {
        inputs: "A list of SAM/BAM/VCF files to fingerprint."
        haplotypeMap: "The file that lists a set of SNPs, optionally arranged in high-LD blocks, to be used for fingerprinting."
        outputPrefix: "Text to prepend to all output."
        crosscheckBy: "Specificies which data-type should be used as the basic comparison unit. Fingerprints from readgroups can be 'rolled-up' to the LIBRARY, SAMPLE, or FILE level before being compared. Fingerprints from VCF can be be compared by SAMPLE or FILE."
        picardMaxMemMb: {
            description: "Passed to Java -Xmx (in Mb).",
            vidarr_retry: true
        }
        exitCodeWhenMismatch: "When one or more mismatches between groups is detected, exit with this value instead of 0."
        exitCodeWhenNoValidChecks: "When all LOD score are zero, exit with this value."
        lodThreshold: "If any two groups (with the same sample name) match with a LOD score lower than the threshold the tool will exit with a non-zero code to indicate error. Program will also exit with an error if it finds two groups with different sample name that match with a LOD score greater than -LOD_THRESHOLD. LOD score 0 means equal likelihood that the groups match vs. come from different individuals, negative LOD score -N, mean 10^N time more likely that the groups are from different individuals, and +N means 10^N times more likely that the groups are from the same individual."
        validationStringency: "Validation stringency for all SAM files read by this program. Setting stringency to SILENT can improve performance when processing a BAM file in which variable-length data (read, qualities, tags) do not otherwise need to be decoded. See https://jira.oicr.on.ca/browse/GC-8372 for why this is set to SILENT for OICR purposes."
        modules: "Modules to load for this workflow."
        threads: "Requested CPU threads."
        jobMemory: {
            description: "Memory (GB) allocated for this job.",
            vidarr_retry: true
        }
        timeout: "Number of hours before task timeout."
    }

    command <<<
        set -eu -o pipefail

        java -Xmx~{picardMaxMemMb}M -jar $PICARD_ROOT/picard.jar CrosscheckFingerprints \
        ~{sep=" " inputCommand} \
        HAPLOTYPE_MAP=~{haplotypeMap} \
        OUTPUT=~{outputPrefix}.crosscheck_metrics.txt \
        MATRIX_OUTPUT=~{outputPrefix}.crosscheck_metrics.matrix \
        NUM_THREADS=~{threads} \
        EXIT_CODE_WHEN_MISMATCH=~{exitCodeWhenMismatch} \
        EXIT_CODE_WHEN_NO_VALID_CHECKS=~{exitCodeWhenNoValidChecks} \
        CROSSCHECK_BY=~{crosscheckBy} \
        LOD_THRESHOLD=~{lodThreshold} \
        VALIDATION_STRINGENCY=~{validationStringency}
    >>>

    output {
        File crosscheckMetrics = "~{outputPrefix}.crosscheck_metrics.txt"
        File crosscheckMetricsMatrix = "~{outputPrefix}.crosscheck_metrics.matrix"
    }

    meta {
        output_meta: {
            crosscheckMetrics: "The crosschecksMetrics file produced by Picard CrosscheckFingerprints",
            crosscheckMetricsMatrix: "Matrix of LOD scores. This is less informative than the metrics output and only contains Normal-Normal LOD score (i.e. doesn't account for Loss of Heterozygosity."
        }
    }

    runtime {
        modules: "~{modules}"
        memory:  "~{jobMemory} GB"
        cpu:     "~{threads}"
        timeout: "~{timeout}"
    }
}
