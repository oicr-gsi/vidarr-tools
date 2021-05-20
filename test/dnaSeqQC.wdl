version 1.0

import "imports/pull_bwaMem.wdl" as bwaMem
import "imports/pull_bamQC.wdl" as bamQC

workflow dnaSeqQC {
    input {
        File fastqR1
        File fastqR2
        String outputFileNamePrefix = basename(fastqR1)
    }

    parameter_meta {
        fastqR1: "fastq file for read 1"
        fastqR2: "fastq file for read 2"
        outputFileNamePrefix: "Optional output prefix for the output"
    }

    call bwaMem.bwaMem {
        input:
            fastqR1 = fastqR1,
            fastqR2 = fastqR2,
            outputFileNamePrefix = outputFileNamePrefix
    }

    call bamQC.bamQC {
        input:
            bamFile = bwaMem.bwaMemBam,
            outputFileNamePrefix = outputFileNamePrefix
    }

    meta {
        author: "Fenglin Chen"
        email: "g3chen@oicr.on.ca"
        description: "Calls the bwaMem-bamQC alignment as a single step."
        dependencies: [
        {
            name: "bwa/0.7.12",
            url: "https://github.com/lh3/bwa/archive/0.7.12.tar.gz"
        },
        {
            name: "samtools/1.9",
            url: "https://github.com/samtools/samtools/archive/0.1.19.tar.gz"
        },
        {
            name: "cutadapt/1.8.3",
            url: "https://cutadapt.readthedocs.io/en/v1.8.3/"
        },
        {
            name: "slicer/0.3.0",
            url: "https://github.com/OpenGene/slicer/archive/v0.3.0.tar.gz"
        },
        {
            name: "picard/2.21.2",
            url: "https://broadinstitute.github.io/picard/command-line-overview.html"
        },
        {
            name: "python/3.6",
            url: "https://www.python.org/downloads/"
        },
        {
            name: "bam-qc-metrics/0.2.5",
            url: "https://github.com/oicr-gsi/bam-qc-metrics.git"
        },
        {
            name: "mosdepth/0.2.9",
            url: "https://github.com/brentp/mosdepth"
        }
      ]
      output_meta: {
        log: "log file for bwaMem task",
        cutAdaptAllLogs: "log file for cutadapt task",
        result: "bamQC report"
      }
    }

 

  output {
     # bwaMem outputs
     File? log = bwaMem.log
     File? cutAdaptAllLogs = bwaMem.cutAdaptAllLogs

     # bamQC outputs
     File result = bamQC.result
  }
}

