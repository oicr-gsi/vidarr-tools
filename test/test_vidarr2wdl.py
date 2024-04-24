import json
import os

import vidarr.wdl


def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


def compare_wdl(base_name: str) -> bool:
    with open(os.path.join(os.path.dirname(__file__), base_name + ".json"), "r") as golden:
        assert ordered(vidarr.wdl.parse(
            os.path.join(
                os.path.dirname(__file__),
                base_name +
                ".wdl"))) == ordered(json.load(golden))


def tests_fastqc():
    compare_wdl("fastqc")


def tests_bcl2fastq():
    compare_wdl("bcl2fastq")


def tests_star():
    compare_wdl("star")


def tests_fingerprintCompare():
    compare_wdl("fingerprintCompare")


def tests_dnaSeqQc():
    compare_wdl("dnaSeqQC")


def tests_bmpp():
    compare_wdl("bamMergePreprocessing")

def tests_empty():
    compare_wdl("empty")
