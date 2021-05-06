version 1.0

workflow fingerprintCollector {
input {
    # only one bam is used as an input
    Int runFinCreator_jobMemory = 8
    Int runFinCreator_timeout = 10
    Array[String] runFinCreator_chroms = ["chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8", "chr9", "chr10", "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17", "chr18", "chr19", "chr20", "chr21", "chr22", "chrX"]
    String runFinCreator_modules
    Int runDepthOfCoverage_timeout = 24
    Int runDepthOfCoverage_jobMemory = 8
    String runDepthOfCoverage_modules
    Float runHaplotypeCaller_stdCC = 30.0
    Int runHaplotypeCaller_timeout = 24
    Int runHaplotypeCaller_jobMemory = 8
    String runHaplotypeCaller_modules
    File inputBam
    File inputBai
    String refFasta
    String hotspotSNPs
    String outputFileNamePrefix = basename(inputBam, ".bam")
}

# Configure and run Fingerprint Collector
call runHaplotypeCaller { input: inputBam = inputBam, inputBai = inputBai, sampleID = outputFileNamePrefix, refFasta = refFasta, hotspotSNPs = hotspotSNPs, modules = runHaplotypeCaller_modules, jobMemory = runHaplotypeCaller_jobMemory, timeout = runHaplotypeCaller_timeout, stdCC = runHaplotypeCaller_stdCC }

call runDepthOfCoverage { input: inputBam = inputBam, inputBai = inputBai, sampleID = outputFileNamePrefix, refFasta = refFasta, hotspotSNPs = hotspotSNPs, modules = runDepthOfCoverage_modules, jobMemory = runDepthOfCoverage_jobMemory, timeout = runDepthOfCoverage_timeout }

call runFinCreator { input: inputVcf = runHaplotypeCaller.vcf, inputCoverage = runDepthOfCoverage.depth, sampleID = outputFileNamePrefix, hotspotSNPs = hotspotSNPs, modules = runFinCreator_modules, chroms = runFinCreator_chroms, timeout = runFinCreator_timeout, jobMemory = runFinCreator_jobMemory}

parameter_meta {
    runFinCreator_jobMemory: "memory allocated for Job"
    runFinCreator_timeout: "Timeout in hours, needed to override imposed limits"
    runFinCreator_chroms: "Canonical chromosomes in desired order (used for soting lines in .fin file)"
    runFinCreator_modules: "Names and versions of modules"
    runDepthOfCoverage_timeout: "Timeout in hours, needed to override imposed limits"
    runDepthOfCoverage_jobMemory: "memory allocated for Job"
    runDepthOfCoverage_modules: "Names and versions of modules"
    runHaplotypeCaller_stdCC: "standard call confidence score, default is 30"
    runHaplotypeCaller_timeout: "Timeout in hours, needed to override imposed limits"
    runHaplotypeCaller_jobMemory: "memory allocated for Job"
    runHaplotypeCaller_modules: "Names and versions of modules"
  inputBam: "Input lane-level BAM file"
  inputBai: "Index for the input BAM file"
  refFasta: "Path to the reference fasta file"
  hotspotSNPs: "Path to the gzipped hotspot vcf file"
  outputFileNamePrefix: "Output prefix, customizable. Default is the input file's basename."
}

meta {
  author: "Peter Ruzanov"
  email: "peter.ruzanov@oicr.on.ca"
  description: "FingerprintCollector 2.1, workflow that generates genotype fingerprints consumed by SampleFingerprinting workflow"
  dependencies: [
      {
        name: "gatk/4.1.7.0, gatk/3.6.0",
        url: "https://gatk.broadinstitute.org"
      },
      {
        name: "tabix/0.2.6",
        url: "http://www.htslib.org"
      },
      {
        name: "python/3.6",
        url: "https://www.python.org/"
      }
    ]
    output_meta: {
      outputVcf: "gzipped vcf expression levels for all genes recorded in the reference",
      outbutTbi: "expression levels for all isoforms recorded in the reference",
      outputFin: "Custom format file, shows which hotspots were called as variants"
    }
}

output {
  File outputVcf = runHaplotypeCaller.vgz
  File outbutTbi = runHaplotypeCaller.tbi
  File outputFin = runFinCreator.finFile
}

}

# ==========================================
#  configure and run HaplotypeCaller
# ==========================================
task runHaplotypeCaller {
input {
 File inputBam
 File inputBai
 String modules
 String refFasta
 String sampleID
 String hotspotSNPs
 Int jobMemory = 8
 Int timeout = 24
 Float stdCC = 30.0
}

parameter_meta {
 inputBam: "input .bam file"
 inputBai: "index of the input .bam file"
 refFasta: "Path to reference FASTA file"
 sampleID: "prefix for making names for output files"
 hotspotSNPs: "Hotspot SNPs are the locations of variants used for genotyping"
 stdCC: "standard call confidence score, default is 30"
 jobMemory: "memory allocated for Job"
 modules: "Names and versions of modules"
 timeout: "Timeout in hours, needed to override imposed limits"
}

command <<<
 set -euo pipefail
 $GATK_ROOT/bin/gatk HaplotypeCaller \
                    -R ~{refFasta} \
                    -I ~{inputBam} \
                    -O ~{sampleID}.snps.raw.vcf \
                   --read-filter CigarContainsNoNOperator \
                   --stand-call-conf ~{stdCC} \
                    -L ~{hotspotSNPs}

 $TABIX_ROOT/bin/bgzip -c ~{sampleID}.snps.raw.vcf > ~{sampleID}.snps.raw.vcf.gz
 $TABIX_ROOT/bin/tabix -p vcf ~{sampleID}.snps.raw.vcf.gz 
>>>

runtime {
  memory:  "~{jobMemory} GB"
  modules: "~{modules}"
  timeout: "~{timeout}"
}

output {
  File vcf = "~{sampleID}.snps.raw.vcf"
  File vgz = "~{sampleID}.snps.raw.vcf.gz"
  File tbi = "~{sampleID}.snps.raw.vcf.gz.tbi"
}
}


# ==========================================
#  configure and run DepthOfCoverage
# ==========================================
task runDepthOfCoverage {
input {
 File inputBam
 File inputBai
 String modules
 String refFasta
 String sampleID
 String hotspotSNPs
 Int jobMemory = 8
 Int timeout = 24
}

parameter_meta {
 inputBam: "input .bam file"
 inputBai: "index of the input .bam file"
 refFasta: "Path to reference FASTA file"
 sampleID: "prefix for making names for output files"
 hotspotSNPs: "Hotspot SNPs are the locations of variants used for genotyping"
 jobMemory: "memory allocated for Job"
 modules: "Names and versions of modules"
 timeout: "Timeout in hours, needed to override imposed limits"
}

command <<<
 $JAVA_ROOT/bin/java -jar $GATK_ROOT/GenomeAnalysisTK.jar \
                     -R ~{refFasta} \
                     -T DepthOfCoverage \
                     -I ~{inputBam} \
                     -o ~{sampleID} \
                     -filterRNC \
                     -L ~{hotspotSNPs} 

>>>

runtime {
  memory:  "~{jobMemory} GB"
  modules: "~{modules}"
  timeout: "~{timeout}"
}

output {
  File depth = "~{sampleID}.sample_interval_summary"
}
}

# ===========================================
#  create a .fin file with runFinCreator task
# ===========================================
task runFinCreator {
input {
  File inputVcf
  File inputCoverage
  File hotspotSNPs
  String sampleID
  String modules
  Array[String] chroms = ["chr1","chr2","chr3","chr4","chr5","chr6","chr7","chr8","chr9","chr10","chr11","chr12","chr13","chr14","chr15","chr16","chr17","chr18","chr19","chr20","chr21","chr22","chrX"]
  Int timeout = 10
  Int jobMemory = 8
}

parameter_meta {
 inputVcf: "Input .bam file for analysis sample"
 inputCoverage: "Optional input .bam file for control sample"
 hotspotSNPs: "Hotspot vcf, used as a reference"
 sampleID: "This is used as a prefix for output files"
 jobMemory: "memory allocated for Job"
 modules: "Names and versions of modules"
 chroms: "Canonical chromosomes in desired order (used for soting lines in .fin file)"
 timeout: "Timeout in hours, needed to override imposed limits"
}

command <<<
 python3 <<CODE
 import gzip
 import re

 flags = {"zerocov": "N",  # No coverage
          "nosnp": "M"}  # no SNP, base matches the reference

 # Read lines from the file with reference SNPs
 refFile = gzip.open("~{hotspotSNPs}", mode='r')
 refLines = refFile.readlines()
 refFile.close()

 # Retrieve reference SNPsb"abcde".decode("utf-8")
 refs = {}
 for rLine in refLines:
     refLine = rLine.decode('utf-8')
     if refLine.strip().startswith('#'):
         continue
     temp = refLine.split("\t")
     if not refs.get(temp[0]):
         refs[temp[0]] = {}
     refs[temp[0]][temp[1]] = dict(flag=flags['zerocov'], dbsnp=temp[2], ref=temp[3])

 # Read lines from the file with Depth data
 depthFile = open("~{inputCoverage}", mode='r')
 depthLines = depthFile.readlines()
 depthFile.close()

 # Retrieve Depth values
 for dLine in depthLines:
     if dLine.startswith("Locus"):
         continue
     temp = dLine.split("\t")
     coords = temp[0].split(":")
     if len(coords) != 2:
         continue
     if refs[coords[0]].get(coords[1]) and int(temp[1]) > 0:
         refs[coords[0]][coords[1]]['flag'] = flags['nosnp']
     else:
         refs[coords[0]][coords[1]]['flag'] = flags['zerocov']

 # Read lines from the file with Depth data
 callFile = open("~{inputVcf}", mode='r')
 callLines = callFile.readlines()
 callFile.close()

 for cLine in callLines:
     if cLine.startswith('#'):
         continue
     temp = cLine.split("\t")
     if refs[temp[0]] and refs[temp[0]].get(temp[1]):
         variant = temp[4].upper()
         if re.fullmatch('[ACGT]{1}', variant) and temp[4] != temp[3]:
             refs[temp[0]][temp[1]]["flag"] = variant
         else:
             refs[temp[0]][temp[1]]["flag"] = flags['nosnp']

 # Prepare lines for printing
 finLines = []
 for chr in ["~{sep='\",\"' chroms}"]:
     if not refs.get(chr):
         continue
     for start in sorted(refs[chr].keys()):
         snp = [refs[chr][start]['ref']]
         if refs[chr][start]['flag'] == 'M':
             snp.append(refs[chr][start]['ref'])
         else:
             snp.append(refs[chr][start]['flag'])
         if refs[chr][start]['flag'] == 'N':
             snp = [""]
         snpflag = "".join(snp)
         finLines.append("\t".join([chr, start, refs[chr][start]['dbsnp'], snpflag, refs[chr][start]['flag']]))

 # Print into a .fin file
 finHeader = ["CHROM", "POS", "ID", "SNP", "FLAG"]
 f = open("~{sampleID}.fin", "w+")
 f.write('\t'.join(finHeader) + '\n')
 f.write('\n'.join(finLines) + '\n')
 f.close()
 
 CODE
>>>

runtime {
  memory:  "~{jobMemory} GB"
  modules: "~{modules}"
  timeout: "~{timeout}"
}

output {
  File finFile = "~{sampleID}.fin"
}
}
