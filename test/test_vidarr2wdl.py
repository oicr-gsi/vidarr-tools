import json
import os

import vidarr.wdl


def compare_wdl(base_name: str) -> bool:
    with open(os.path.join(os.path.dirname(__file__), base_name + ".json"), "r") as golden:
        assert vidarr.wdl.parse(
            os.path.join(
                os.path.dirname(__file__),
                base_name +
                ".wdl")) == json.load(golden)


def test_fastqc():
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
