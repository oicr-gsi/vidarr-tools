version 1.0

struct GenomeResources {
    String fasta
    String genomeModule
}

workflow methylDackel {
    input {
        File bam
        File bai
        String outputFileNamePrefix
        String reference
        Boolean doMbias = true
    }

    parameter_meta {
        bam: "The bam file for methyl analysis"
        bai: "The index for input bam"
        outputFileNamePrefix: "Prefix for output files"
        reference: "The genome reference build"
        doMbias: "Whether run Mbias or not "
    }

    Map[String, GenomeResources] resources = {
        "hg38": {
            "fasta": "$HG38_EM_SEQ_ROOT/hg38_random.fa",
            "genomeModule": "hg38-em-seq/p12-2022-10-17"
        }
    }

    GenomeResources ref = resources[reference]

    call methylDackelExtract {
        input:
            bam = bam,
            bai = bai,
            outputFileNamePrefix = outputFileNamePrefix,
            fasta = ref.fasta,
            modules = "methyldackel/0.6.1 ~{ref.genomeModule}"
    }

    if ( doMbias ){
        call extractChromosomes{
            input:
            bam = bam
        }

        scatter ( chr in extractChromosomes.chromosomes ) {
            call methylDackelMbias {
                input:
                    bam = bam,
                    bai = bai,
                    chr = chr,
                    fasta = ref.fasta,
                    outputFileNamePrefix = outputFileNamePrefix,
                    modules = "methyldackel/0.6.1 samtools/1.16.1 ~{ref.genomeModule}"
            }
        }      
    
        Array[File?] mbiasTsvs = methylDackelMbias.mbias_tsv
        Array[File?] mbiasSvg = methylDackelMbias.mbias_svg_files

        if (length(mbiasSvg) > 0) {
            File? mbias_svg_output = mbiasSvg[0]
        }

        call concatMbiasTsvFiles {
            input:
                inputTsvs = mbiasTsvs,
                outputFileNamePrefix = outputFileNamePrefix
        }
    }

    meta {
        author: "Gavin Peng"
        email: "gpeng@oicr.on.ca"
        description: "Workflow to run methylDackel, will process a coordinate-sorted and indexed BAM or CRAM file containing some form of BS-seq or EM-seq alignments and extract per-base methylation metrics from them. The extract task generates bedGraph files, by default generates only CpG metrics, option can be set to also generate CHH and CHG metrics. Mbias task generates tsv file for methylation bias metrics and a svg graph for visualizing mbias (only for chromosome 1 here)."
        dependencies: [
         {
            name: "methyldackel/0.6.1",
            url: "https://github.com/dpryan79/MethylDackel"
                        }
        ]
        output_meta: {
            extract_bedgraph: {
                description: "bedGraph output from methylDackelExtract",
                vidarr_label: "extract_bedgraph"
            },
            mbias_tsv: {
                description: "mbias tsv output from methylDackelMbias",
                vidarr_label: "mbias_tsv"
            },
            mbias_svg: {
                description: "svg plot files from methylDackelMbias",
                vidarr_label: "mbias_svg"
            }
        }
    }

    output {
        File extract_CpGbedgraph = methylDackelExtract.CpG_graph
        File? extract_CHGbedgraph = methylDackelExtract.CHG_graph
        File? extract_CHHbedgraph = methylDackelExtract.CHH_graph
        File? mbias_tsv = concatMbiasTsvFiles.combinedTsv
        File? mbias_svg = mbias_svg_output
    }
}

task extractChromosomes {
    input {
        File bam
        Int timeout = 1
        Int memory = 1
        Int threads = 1
        String modules = "samtools/1.16.1"
    }

    parameter_meta {
        timeout: "The hours until the task is killed"
        memory: "The GB of memory provided to the task"
        threads: "The number of threads the task has access to"
        modules: "The modules that will be loaded"
    }

    command <<<
        samtools view -H ~{bam} | grep @SQ | cut -f2 | sed 's/SN://' | grep -E -v '(_random|chrUn|chrM|MT|_alt|_fix|_decoy|_PATCH|_HSCHR|NC_|_EBV|EBV|phiX|pUC19|lambda|_scaffold)'
    >>>

    output {
        Array[String] chromosomes = read_lines(stdout())
    }

    runtime {
        modules: "~{modules}"
        memory:  "~{memory} GB"
        cpu:     "~{threads}"
        timeout: "~{timeout}"
    }
}

task methylDackelExtract {
    input {
        File bam
        File bai
        String outputFileNamePrefix
        String fasta
        Boolean doCHH = false
        Boolean doCHG = false
        Boolean mergeContext = false
        Int? minimumuQualityPhred
        Int? minimumMAPQ
        Int? minDepth 
        Int timeout = 8
        Int memory = 16
        Int threads = 8
        String modules
    }

    parameter_meta {
        bam: "The bam file to analyze"
        bai: "The .bai index of the bam file"
        outputFileNamePrefix: "Output file name prefix"
        fasta: "FastA file used for alignment"
        doCHH: "whether enable CHH metrics"
        doCHG: "whether enable CHG metrics"
        mergeContext: "whether merge context in bedgraph"
        minimumuQualityPhred: "minimumu sequencing quality phred score"
        minimumMAPQ: "minimum MAPQ score"
        minDepth: "region with minimum depth needed to be included in analysis"
        timeout: "The hours until the task is killed"
        memory: "The GB of memory provided to the task"
        threads: "The number of threads the task has access to"
        modules: "The modules that will be loaded"
    }
    String optionCHH = if doCHH then "--CHH" else ""
    String optionCHG = if doCHG then "--CHG" else ""
    String optionMergeContext = if mergeContext then "--mergeContext" else ""
    String filterMAPQ = if defined(minimumMAPQ) then "-q ~{minimumMAPQ}" else ""
    String filterQalityPhred = if defined(minimumuQualityPhred) then "-p ~{minimumuQualityPhred}" else ""
    String filterminDepth = if defined(minDepth) then "--minDepth ~{minDepth}" else ""

     command <<<
        set -euo pipefail
        MethylDackel extract ~{filterMAPQ} ~{filterQalityPhred} ~{filterminDepth} ~{optionMergeContext} ~{optionCHH} ~{optionCHG} -@ ~{threads} ~{fasta} ~{bam} -o ~{outputFileNamePrefix}.methyldackel
        
    >>>

    output {
        File CpG_graph = "~{outputFileNamePrefix}.methyldackel_CpG.bedGraph"
        File? CHG_graph = "~{outputFileNamePrefix}.methyldackel_CHG.bedGraph"
        File? CHH_graph = "~{outputFileNamePrefix}.methyldackel_CHH.bedGraph"
    }

    meta {
        output_meta: {
            CpG_graph: "The MethylDackel result bedGraph for CpG sequence context",
            CHG_graph: "The MethylDackel result bedGraph for CHG sequence context",
            CHH_graph: "The MethylDackel result bedGraph for CHH sequence context"
        }
    }

    runtime {
        modules: "~{modules}"
        memory:  "~{memory} GB"
        cpu:     "~{threads}"
        timeout: "~{timeout}"
    }
}

task methylDackelMbias {
    input {
        File bam
        File bai
        String chr
        String fasta
        String outputFileNamePrefix
        String modules
        Int timeout = 12
        Int memory = 8
        Int threads = 8
    }

    parameter_meta {
        bam: "The bam file to analyze"
        bai: "The .bai index of the bam file"
        chr: "The region to call methylDackel mbias"
        fasta: "FastA file used for alignment"
        outputFileNamePrefix: "Output file name prefix"
        timeout: "The hours until the task is killed"
        memory: "The GB of memory provided to the task"
        threads: "The number of threads the task has access to"
        modules: "The modules that will be loaded"
    }

    command <<<
        MethylDackel mbias --txt -r ~{chr} ~{fasta} ~{bam} ~{outputFileNamePrefix}.mbias > output_mbias.tsv
        tar  -czf ~{outputFileNamePrefix}_mbias.svgs.tar.gz *.svg
    >>>

    output {
        File? mbias_tsv = "output_mbias.tsv"
        File? mbias_svg_files = "~{outputFileNamePrefix}_mbias.svgs.tar.gz"
    }
    
    meta {
        output_meta: {
            mbias_tsv: "mbias tsv output from methylDackelMbias",
            mbias_svg_files: "svg plot files from methylDackelMbias"
        }
    }
    
    runtime {
        modules: "~{modules}"
        memory:  "~{memory} GB"
        cpu:     "~{threads}"
        timeout: "~{timeout}"
    }
}

task concatMbiasTsvFiles {
    input {
        Array[File?] inputTsvs
        String outputFileNamePrefix
        Int timeout = 1
        Int memory = 1
        Int threads = 1
        String modules = "pandas/2.1.3"
    }
    parameter_meta {
        inputTsvs: "Array of mbias tsv files"
        outputFileNamePrefix: "Output file name prefix"
        timeout: "The hours until the task is killed"
        memory: "The GB of memory provided to the task"
        threads: "The number of threads the task has access to"
        modules: "The modules that will be loaded"
    }

    command <<<
        python3<<CODE

        import sys
        import pandas as pd

        dfs = []
        input_files = ['~{sep="', '" select_all(inputTsvs)}']
        columns = ['Strand', 'Read', 'Position', 'nMethylated', 'nUnmethylated']
        for file in input_files:
            df = pd.read_csv(file, sep='\t', skiprows=1, names=columns)  # Skip header
            dfs.append(df)

        combined_df = pd.concat(dfs, ignore_index=True)

        # Group by Strand, Read, and Position, and sum the methylation counts
        aggregated_df = combined_df.groupby(['Strand', 'Read', 'Position'], as_index=False).agg({
            'nMethylated': 'sum',
            'nUnmethylated': 'sum'
        }).sort_values(['Strand', 'Read', 'Position'])

        with open("~{outputFileNamePrefix}.mbias.tsv", 'w') as f:
            aggregated_df.to_csv(f, sep='\t', index=False)
        CODE
    >>>

    output {
        File combinedTsv = "~{outputFileNamePrefix}.mbias.tsv"
    }
    runtime {
        modules: "~{modules}"
        memory:  "~{memory} GB"
        cpu:     "~{threads}"
        timeout: "~{timeout}"
    }
}